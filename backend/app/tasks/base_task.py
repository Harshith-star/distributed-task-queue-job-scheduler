"""
tasks/base_task.py

Base Celery task that wraps every execution with:
  - DB record lifecycle (running → completed / failed)
  - Structured logging
  - Automatic retry with exponential backoff
  - Email notification on completion / failure
  - WebSocket broadcast (via Redis pub/sub)
"""
import asyncio
import socket
import traceback
from datetime import datetime, timezone

from celery import Task
from celery.utils.log import get_task_logger

from app.workers.celery_app import celery_app

logger = get_task_logger(__name__)


class BaseTaskQ(Task):
    """Abstract base for all TaskQ task types.

    Subclasses implement `run_task(config: dict) -> str`.
    """
    abstract = True

    def run_task(self, config: dict) -> str:  # noqa: ANN001
        """Override in subclass — business logic goes here."""
        raise NotImplementedError

    def _get_db_session(self):
        """Synchronously create an async DB session using asyncio.run()."""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from app.core.config import get_settings
        settings = get_settings()
        # Sync URL for use inside Celery (converts asyncpg → psycopg2)
        sync_url = settings.DATABASE_URL.replace("+asyncpg", "")
        from sqlalchemy import create_engine as ce
        engine = ce(sync_url, pool_pre_ping=True)
        Session = sessionmaker(bind=engine)
        return Session()

    def run(self, execution_id: int, task_id: int, config: dict) -> str:
        """Called by Celery. Orchestrates the full execution lifecycle."""
        from app.models.task_execution import ExecutionStatus

        db = self._get_db_session()
        try:
            from app.models.task_execution import TaskExecution
            execution = db.get(TaskExecution, execution_id)
            if execution is None:
                logger.error("Execution %s not found", execution_id)
                return "error:execution_not_found"

            # Mark running
            execution.status = ExecutionStatus.RUNNING
            execution.started_at = datetime.now(tz=timezone.utc)
            execution.worker_name = socket.gethostname()
            execution.celery_task_id = self.request.id
            db.commit()
            self._broadcast(execution_id, "running", task_id)

            # Execute task logic
            logger.info("Starting task_id=%s execution_id=%s worker=%s", task_id, execution_id, socket.gethostname())
            result = self.run_task(config)

            # Mark completed
            now = datetime.now(tz=timezone.utc)
            execution.status = ExecutionStatus.COMPLETED
            execution.completed_at = now
            execution.duration_ms = (now - execution.started_at).total_seconds() * 1000 if execution.started_at else None
            execution.result = str(result)
            db.commit()

            self._broadcast(execution_id, "completed", task_id)
            self._notify(db, task_id, execution_id, success=True)
            logger.info("Completed execution_id=%s duration=%.2fms", execution_id, execution.duration_ms or 0)
            return result

        except Exception as exc:
            err_msg = str(exc)
            logs    = traceback.format_exc()
            logger.error("Failed execution_id=%s error=%s", execution_id, err_msg)

            try:
                from app.models.task_execution import TaskExecution, ExecutionStatus
                execution = db.get(TaskExecution, execution_id)
                if execution:
                    retry_count = execution.retry_count
                    # Get max_retries from task
                    from app.models.task import Task as TaskModel
                    task_obj = db.get(TaskModel, task_id)
                    max_retries = task_obj.max_retries if task_obj else 3

                    if retry_count < max_retries:
                        execution.status = ExecutionStatus.RETRYING
                        execution.retry_count += 1
                        db.commit()
                        self._broadcast(execution_id, "retrying", task_id)
                        # Exponential backoff: 60s, 120s, 240s...
                        countdown = 60 * (2 ** retry_count)
                        raise self.retry(exc=exc, countdown=countdown, max_retries=max_retries)
                    else:
                        now = datetime.now(tz=timezone.utc)
                        execution.status = ExecutionStatus.FAILED
                        execution.completed_at = now
                        if execution.started_at:
                            execution.duration_ms = (now - execution.started_at).total_seconds() * 1000
                        execution.failure_reason = err_msg
                        execution.logs = logs
                        db.commit()
                        self._broadcast(execution_id, "failed", task_id)
                        self._notify(db, task_id, execution_id, success=False, reason=err_msg)
            except self.MaxRetriesExceededError:
                raise
            except Exception as inner:
                logger.error("Error updating execution record: %s", inner)
            finally:
                db.close()
            raise
        finally:
            try:
                db.close()
            except Exception:
                pass

    def _broadcast(self, execution_id: int, status: str, task_id: int) -> None:
        """Publish status update to Redis pub/sub for WebSocket consumers."""
        try:
            import redis, json
            from app.core.config import get_settings
            r = redis.from_url(get_settings().REDIS_URL)
            r.publish("task_events", json.dumps({
                "type": "execution_update",
                "execution_id": execution_id,
                "task_id": task_id,
                "status": status,
            }))
            r.close()
        except Exception as e:
            logger.warning("Failed to broadcast status: %s", e)

    def _notify(self, db, task_id: int, execution_id: int, success: bool, reason: str = "") -> None:
        """Create in-app notification and send email."""
        try:
            from app.models.task import Task as TaskModel
            from app.models.notification import Notification, NotificationType
            task = db.get(TaskModel, task_id)
            if not task:
                return
            notif_type = NotificationType.SUCCESS if success else NotificationType.FAILURE
            title   = f"Task {'Completed' if success else 'Failed'}: {task.name}"
            message = f"Task '{task.name}' {'completed successfully' if success else f'failed: {reason}'}."
            notif = Notification(
                user_id=task.user_id, task_id=task_id, execution_id=execution_id,
                type=notif_type, title=title, message=message,
            )
            db.add(notif)
            db.commit()
        except Exception as e:
            logger.warning("Failed to create notification: %s", e)
