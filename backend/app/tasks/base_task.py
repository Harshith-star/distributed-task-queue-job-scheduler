"""Base Celery task — owns the execution lifecycle, status transitions, notifications."""
import json
import socket
import traceback
from datetime import datetime, timezone

import redis
from celery import Task as CeleryTask
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.task import Task
from app.models.task_execution import ExecutionStatus, TaskExecution
from app.models.notification import Notification

logger = get_logger(__name__)
settings = get_settings()

# Celery workers are synchronous processes. Do NOT reuse the async engine here —
# asyncio.run() per task creates a new event loop each call and corrupts the pool.
_sync_url = (
    settings.DATABASE_URL
    .replace("+asyncpg", "+psycopg2")
    .replace("+aiosqlite", "")
)
_engine = create_engine(_sync_url, pool_pre_ping=True, pool_recycle=1800)
SyncSession = sessionmaker(bind=_engine, expire_on_commit=False)
_redis = redis.from_url(settings.REDIS_URL)


class BaseTaskQ(CeleryTask):
    abstract = True                 # only the BASE is abstract
    acks_late = True
    reject_on_worker_lost = True

    # Subclasses implement this.
    def execute_task(self, config: dict) -> str:
        raise NotImplementedError

    def run(self, execution_id=None, task_id=None, *_legacy):
        """
        args are [execution_id, task_id].
        execution_id may be None (recurring RedBeat entries) — we create one.
        *_legacy absorbs the old third `task_config` arg from messages already
        sitting in the queue, so old payloads don't crash the worker.
        """
        now = datetime.now(timezone.utc)
        worker_id = (self.request.hostname or socket.gethostname())[:64]

        with SyncSession() as db:
            task = db.get(Task, task_id)
            if task is None or getattr(task, "deleted_at", None):
                logger.warning("Task %s missing/deleted, skipping", task_id)
                if execution_id:
                    self._finalize(db, execution_id, ExecutionStatus.FAILED, now,
                                   error="Task no longer exists")
                return "task-missing"

            # --- get or create the execution row ---------------------------
            if execution_id is None:
                execution = TaskExecution(
                    task_id=task.id,
                    status=ExecutionStatus.QUEUED,
                    triggered_by="schedule",
                )
                db.add(execution)
                db.commit()
                db.refresh(execution)
                execution_id = execution.id
            else:
                execution = db.get(TaskExecution, execution_id)
                if execution is None:
                    logger.error("Execution %s not found", execution_id)
                    return "execution-missing"
                if execution.status == ExecutionStatus.CANCELLED:
                    return "cancelled"

            # --- mark RUNNING ----------------------------------------------
            execution.status = ExecutionStatus.RUNNING
            execution.started_at = now
            execution.worker_name = worker_id
            execution.celery_task_id = self.request.id
            db.commit()
            self._publish(task, execution, "running")

            # --- execute -----------------------------------------------------
            try:
                # Config is read fresh from the DB, never from the message payload.
                output = self.execute_task(task.task_config or {})
            except Exception as exc:
                logger.exception("Execution %s failed", execution_id)
                self._finalize(db, execution_id, ExecutionStatus.FAILED, now,
                               error=f"{type(exc).__name__}: {exc}",
                               trace=traceback.format_exc()[-4000:])
                raise                      # let Celery record + retry if configured

            self._finalize(db, execution_id, ExecutionStatus.COMPLETED, now, output=output)
            return output

    # ------------------------------------------------------------------ utils
    def _finalize(self, db, execution_id, status, started_at,
                  output=None, error=None, trace=None):
        finished = datetime.now(timezone.utc)
        execution = db.get(TaskExecution, execution_id)
        if execution is None:
            return

        execution.status = status
        execution.completed_at = finished
        execution.duration_ms = int((finished - (execution.started_at or started_at))
                                    .total_seconds() * 1000)
        if output is not None:
            execution.result = str(output)[:8000]
        if error is not None:
            execution.failure_reason = error[:2000]
        if trace is not None and hasattr(execution, "traceback"):
            execution.traceback = trace

        task = db.get(Task, execution.task_id)
        ok = status == ExecutionStatus.COMPLETED

        db.add(Notification(
            user_id=task.user_id,
            task_id=task.id,
            execution_id=execution.id,
            type="success" if ok else "failure",
            title=f"Task {'Completed' if ok else 'Failed'}: {task.name}",
            message=(output if ok else error) or "",
            is_read=False,
        ))
        db.commit()
        self._publish(task, execution, "success" if ok else "failed",
                      message=(output if ok else error))

    def _publish(self, task, execution, event, message=None):
        """Publish to the OWNER's channel only."""
        try:
            _redis.publish(f"task_events:{task.user_id}", json.dumps({
                "type": "execution_update",
                "event": event,
                "task_id": task.id,
                "task_name": task.name,
                "execution_id": execution.id,
                "status": execution.status.value,
                "message": message,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }, default=str))
        except Exception:
            logger.warning("Failed to publish event for execution %s", execution.id)