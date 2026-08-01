"""Task service — orchestrates task creation, updates, scheduling, and execution."""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from celery.schedules import crontab
from redbeat import RedBeatSchedulerEntry
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.exceptions.domain import (
    ForbiddenError, NotFoundError, TaskCannotBeCancelledError,
    TaskNotFoundError, TaskNotRetriableError,
)
from app.models.task import Task, TaskStatus, ScheduleType
from app.models.task_execution import ExecutionStatus, TaskExecution
from app.repositories.task_repository import TaskRepository
from app.repositories.execution_repository import ExecutionRepository
from app.repositories.audit_notification_repository import AuditRepository
from app.workers.celery_app import celery_app

logger = get_logger(__name__)

TASK_NAME_MAP = {
    "email":        "app.tasks.email_task.send_email",
    "http":         "app.tasks.http_task.http_request",
    "file_cleanup": "app.tasks.file_cleanup_task.cleanup",
    "db_backup":    "app.tasks.db_backup_task.backup",
    "custom":       "app.tasks.custom_task.run_custom",
}
DEFAULT_TIMEOUT = 300


class TaskService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db                       # ONE session for the whole request
        self._task_repo = TaskRepository(db)
        self._exec_repo = ExecutionRepository(db)
        self._audit_repo = AuditRepository(db)

    # ------------------------------------------------------------------ CRUD
    async def create_task(self, user_id: int, data: dict, ip: str = "") -> Task:
        from app.models.schedule import Schedule

        task = await self._task_repo.create(user_id=user_id, **data)
        self._db.add(Schedule(task_id=task.id))
        await self._db.flush()              # get task.id without committing yet

        # If this raises, the whole transaction rolls back — no phantom task.
        await self._schedule_task(task)

        await self._audit_repo.log(
            action="task.create", resource_type="task",
            user_id=user_id, resource_id=str(task.id),
            details={"name": task.name, "type": task.task_type.value},
            ip_address=ip,
        )
        await self._db.commit()
        await self._db.refresh(task)
        logger.info("Task created task_id=%s user_id=%s", task.id, user_id)
        return task

    async def update_task(self, task_id: int, user_id: int, data: dict, ip: str = "") -> Task:
        task = await self._task_repo.get_by_id_and_user(task_id, user_id)
        if not task:
            raise TaskNotFoundError()

        for k, v in data.items():
            if v is not None:
                setattr(task, k, v)
        await self._db.flush()

        await self._cancel_pending(task)    # kill the old countdown message
        self._remove_beat_schedule(task)
        if task.status == TaskStatus.ACTIVE:
            await self._schedule_task(task)

        await self._audit_repo.log(
            action="task.update", resource_type="task",
            user_id=user_id, resource_id=str(task_id),
            details={"fields_updated": list(data.keys())}, ip_address=ip,
        )
        await self._db.commit()
        await self._db.refresh(task)
        return task

    async def delete_task(self, task_id: int, user_id: int,
                          is_admin: bool = False, ip: str = "") -> None:
        task = (await self._task_repo.get_by_id_with_schedule(task_id) if is_admin
                else await self._task_repo.get_by_id_and_user(task_id, user_id))
        if not task:
            raise TaskNotFoundError()

        self._remove_beat_schedule(task)
        await self._cancel_pending(task)
        await self._task_repo.soft_delete(task)

        await self._audit_repo.log(
            action="task.delete", resource_type="task",
            user_id=user_id, resource_id=str(task_id),
            details={"name": task.name}, ip_address=ip,
        )
        await self._db.commit()
        logger.info("Task deleted task_id=%s", task_id)

    async def pause_task(self, task_id: int, user_id: int) -> Task:
        task = await self._task_repo.get_by_id_and_user(task_id, user_id)
        if not task:
            raise TaskNotFoundError()
        if task.status == TaskStatus.PAUSED:
            return task

        task.status = TaskStatus.PAUSED
        self._remove_beat_schedule(task)
        await self._cancel_pending(task)
        await self._db.commit()
        await self._db.refresh(task)
        return task

    async def resume_task(self, task_id: int, user_id: int) -> Task:
        task = await self._task_repo.get_by_id_and_user(task_id, user_id)
        if not task:
            raise TaskNotFoundError()

        task.status = TaskStatus.ACTIVE
        await self._db.flush()
        await self._schedule_task(task)
        await self._db.commit()
        await self._db.refresh(task)
        return task

    # ------------------------------------------------------------- execution
    async def trigger_now(self, task_id: int, user_id: int) -> TaskExecution:
        task = await self._task_repo.get_by_id_and_user(task_id, user_id)
        if not task:
            raise TaskNotFoundError()

        execution = await self._dispatch(task, triggered_by="manual")
        await self._audit_repo.log(
            action="task.trigger", resource_type="task_execution",
            user_id=user_id, resource_id=str(execution.id),
            details={"task_id": task_id},
        )
        await self._db.commit()
        await self._db.refresh(execution)
        return execution

    async def retry_execution(self, execution_id: int, user_id: int) -> TaskExecution:
        execution = await self._db.get(TaskExecution, execution_id)
        if not execution:
            raise NotFoundError("Execution not found")
        if execution.status not in (ExecutionStatus.FAILED, ExecutionStatus.CANCELLED):
            raise TaskNotRetriableError()

        task = await self._task_repo.get_by_id_with_schedule(execution.task_id)
        if not task or task.user_id != user_id:
            raise ForbiddenError()

        new_execution = await self._dispatch(task, triggered_by="retry")
        await self._audit_repo.log(
            action="task.retry", resource_type="task_execution",
            user_id=user_id, resource_id=str(new_execution.id),
            details={"original_execution_id": execution_id},
        )
        await self._db.commit()
        await self._db.refresh(new_execution)
        return new_execution

    async def cancel_execution(self, execution_id: int, user_id: int) -> TaskExecution:
        execution = await self._db.get(TaskExecution, execution_id)
        if not execution:
            raise NotFoundError("Execution not found")

        task = await self._task_repo.get_by_id_with_schedule(execution.task_id)
        if not task or task.user_id != user_id:
            raise ForbiddenError()
        if execution.status not in (ExecutionStatus.QUEUED, ExecutionStatus.RUNNING):
            raise TaskCannotBeCancelledError()

        if execution.celery_task_id:
            celery_app.control.revoke(execution.celery_task_id, terminate=True)

        execution.status = ExecutionStatus.CANCELLED
        execution.completed_at = datetime.now(timezone.utc)
        await self._db.commit()
        await self._db.refresh(execution)
        return execution

    # -------------------------------------------------------------- internals
    async def _dispatch(self, task: Task, triggered_by: str) -> TaskExecution:
        """Create an execution row and push it to Celery immediately."""
        celery_task = TASK_NAME_MAP.get(task.task_type.value)
        if celery_task is None:
            raise ValueError(f"Unsupported task_type: {task.task_type.value}")

        timeout = task.timeout_seconds or DEFAULT_TIMEOUT
        execution = await self._exec_repo.create_execution(task.id, triggered_by=triggered_by)
        await self._db.flush()

        result = celery_app.send_task(
            celery_task,
            args=[execution.id, task.id, task.task_config or {},],       # config is read in the worker
            soft_time_limit=timeout,
            time_limit=timeout + 30,
        )
        execution.celery_task_id = result.id    # ← now cancel/revoke actually works
        await self._db.flush()
        return execution

    async def _schedule_task(self, task: Task) -> None:
        """Register the schedule. Raises on failure — do NOT swallow."""
        celery_task = TASK_NAME_MAP.get(task.task_type.value)
        if celery_task is None:
            raise ValueError(f"Unsupported task_type: {task.task_type.value}")

        timeout = task.timeout_seconds or DEFAULT_TIMEOUT

        # ---- one-time: a single delayed message, no beat involved ----------
        if task.schedule_type == ScheduleType.ONE_TIME:
            if not task.scheduled_at:
                raise ValueError("One-time tasks require 'scheduled_at'")

            run_at = task.scheduled_at
            if isinstance(run_at, str):
                run_at = datetime.fromisoformat(run_at.replace("Z", "+00:00"))
            if run_at.tzinfo is None:
                run_at = run_at.replace(tzinfo=ZoneInfo("Asia/Kolkata"))

            delay = max((run_at - datetime.now(timezone.utc)).total_seconds(), 0)
            logger.info("one-time task_id=%s run_at=%s delay=%.1fs",
                        task.id, run_at.isoformat(), delay)

            execution = await self._exec_repo.create_execution(task.id, triggered_by="schedule")
            await self._db.flush()

            result = celery_app.send_task(
                celery_task,
                args=[execution.id, task.id,  task.task_config or {},],
                countdown=delay,
                soft_time_limit=timeout,
                time_limit=timeout + 30,
            )
            execution.celery_task_id = result.id
            await self._db.flush()
            return

        # ---- recurring: RedBeat entry, execution row created at RUN time ---
        entry = RedBeatSchedulerEntry(
            f"taskq:task:{task.id}",
            celery_task,
            self._build_cron(task),
            args=[None, task.id,  task.task_config or {},],              # ← None, not a fixed execution id
            app=celery_app,
        )
        entry.save()

    def _build_cron(self, task: Task):
        if task.schedule_type == ScheduleType.CRON:
            parts = (task.cron_expression or "").strip().split()
            if len(parts) != 5:
                raise ValueError(f"Invalid cron expression: {task.cron_expression!r}")
            minute, hour, dom, month, dow = parts
            return crontab(minute=minute, hour=hour, day_of_month=dom,
                           month_of_year=month, day_of_week=dow)
        try:
            return {
                ScheduleType.DAILY:   crontab(hour=0, minute=0),
                ScheduleType.WEEKLY:  crontab(day_of_week=1, hour=0, minute=0),
                ScheduleType.MONTHLY: crontab(day_of_month=1, hour=0, minute=0),
            }[task.schedule_type]
        except KeyError:
            raise ValueError(f"Unhandled schedule_type: {task.schedule_type}")

    async def _cancel_pending(self, task: Task) -> None:
        """Revoke queued-but-not-started runs so edits don't duplicate sends."""
        rows = await self._db.execute(
            select(TaskExecution).where(
                TaskExecution.task_id == task.id,
                TaskExecution.status == ExecutionStatus.QUEUED,
            )
        )
        for execution in rows.scalars():
            if execution.celery_task_id:
                celery_app.control.revoke(execution.celery_task_id)
            execution.status = ExecutionStatus.CANCELLED
            execution.completed_at = datetime.now(timezone.utc)
        await self._db.flush()

    def _remove_beat_schedule(self, task: Task) -> None:
        try:
            RedBeatSchedulerEntry.from_key(f"taskq:task:{task.id}", app=celery_app).delete()
        except Exception as e:
            logger.debug("No beat entry to remove for task_id=%s (%s)", task.id, e)