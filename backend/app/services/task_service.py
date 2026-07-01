"""Task service — orchestrates task creation, updates, scheduling, and execution."""
from datetime import datetime, timezone
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

logger = get_logger(__name__)


class TaskService:
    def __init__(self, db: AsyncSession) -> None:
        self._task_repo  = TaskRepository(db)
        self._exec_repo  = ExecutionRepository(db)
        self._audit_repo = AuditRepository(db)

    async def create_task(self, user_id: int, data: dict, ip: str = "") -> Task:
        from app.models.schedule import Schedule
        task = await self._task_repo.create(user_id=user_id, **data)

        # Create schedule record in the same session
        schedule = Schedule(task_id=task.id)
        self._task_repo._db.add(schedule)
        await self._task_repo._db.commit()
        await self._task_repo._db.refresh(task)

        # Register with Celery Beat
        await self._register_beat_schedule(task)

        await self._audit_repo.log(
            action="task.create", resource_type="task",
            user_id=user_id, resource_id=str(task.id),
            details={"name": task.name, "type": task.task_type.value},
            ip_address=ip,
        )
        logger.info("Task created task_id=%s user_id=%s", task.id, user_id)
        return task

    async def update_task(self, task_id: int, user_id: int, data: dict, ip: str = "") -> Task:
        task = await self._task_repo.get_by_id_and_user(task_id, user_id)
        if not task:
            raise TaskNotFoundError()

        # Apply updates
        for k, v in data.items():
            if v is not None:
                setattr(task, k, v)

        from app.core.database import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            session.add(task)
            await session.commit()
            await session.refresh(task)

        # Re-register beat schedule with new config
        await self._register_beat_schedule(task)

        await self._audit_repo.log(
            action="task.update", resource_type="task",
            user_id=user_id, resource_id=str(task_id),
            details={"fields_updated": list(data.keys())}, ip_address=ip,
        )
        return task

    async def delete_task(self, task_id: int, user_id: int, is_admin: bool = False, ip: str = "") -> None:
        task = await self._task_repo.get_by_id_and_user(task_id, user_id) if not is_admin else await self._task_repo.get_by_id_with_schedule(task_id)
        if not task:
            raise TaskNotFoundError()

        # Remove from Celery Beat
        self._remove_beat_schedule(task)
        await self._task_repo.soft_delete(task)

        await self._audit_repo.log(
            action="task.delete", resource_type="task",
            user_id=user_id, resource_id=str(task_id),
            details={"name": task.name}, ip_address=ip,
        )
        logger.info("Task deleted task_id=%s", task_id)

    async def pause_task(self, task_id: int, user_id: int) -> Task:
        task = await self._task_repo.get_by_id_and_user(task_id, user_id)
        if not task:
            raise TaskNotFoundError()
        if task.status == TaskStatus.PAUSED:
            return task
        task.status = TaskStatus.PAUSED
        self._remove_beat_schedule(task)
        from app.core.database import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            session.add(task)
            await session.commit()
            await session.refresh(task)
        logger.info("Task paused task_id=%s", task_id)
        return task

    async def resume_task(self, task_id: int, user_id: int) -> Task:
        task = await self._task_repo.get_by_id_and_user(task_id, user_id)
        if not task:
            raise TaskNotFoundError()
        task.status = TaskStatus.ACTIVE
        await self._register_beat_schedule(task)
        from app.core.database import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            session.add(task)
            await session.commit()
            await session.refresh(task)
        logger.info("Task resumed task_id=%s", task_id)
        return task

    async def trigger_now(self, task_id: int, user_id: int) -> TaskExecution:
        """Manually trigger a task immediately."""
        task = await self._task_repo.get_by_id_and_user(task_id, user_id)
        if not task:
            raise TaskNotFoundError()

        execution = await self._exec_repo.create_execution(task_id, triggered_by="manual")
        self._dispatch_to_celery(task, execution.id)

        await self._audit_repo.log(
            action="task.trigger", resource_type="task_execution",
            user_id=user_id, resource_id=str(execution.id),
            details={"task_id": task_id},
        )
        return execution

    async def retry_execution(self, execution_id: int, user_id: int) -> TaskExecution:
        from app.core.database import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            from sqlalchemy import select
            result = await session.execute(
                select(TaskExecution).where(TaskExecution.id == execution_id)
            )
            execution = result.scalar_one_or_none()
        if not execution:
            raise NotFoundError("Execution not found")
        if execution.status not in (ExecutionStatus.FAILED, ExecutionStatus.CANCELLED):
            raise TaskNotRetriableError()

        task = await self._task_repo.get_by_id_with_schedule(execution.task_id)
        if not task or task.user_id != user_id:
            raise ForbiddenError()

        new_execution = await self._exec_repo.create_execution(task.id, triggered_by="retry")
        self._dispatch_to_celery(task, new_execution.id)

        await self._audit_repo.log(
            action="task.retry", resource_type="task_execution",
            user_id=user_id, resource_id=str(new_execution.id),
            details={"original_execution_id": execution_id},
        )
        return new_execution

    async def cancel_execution(self, execution_id: int, user_id: int) -> TaskExecution:
        from app.core.database import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            from sqlalchemy import select
            result = await session.execute(
                select(TaskExecution).where(TaskExecution.id == execution_id)
            )
            execution = result.scalar_one_or_none()
        if not execution:
            raise NotFoundError("Execution not found")
        if execution.status not in (ExecutionStatus.QUEUED, ExecutionStatus.RUNNING):
            raise TaskCannotBeCancelledError()

        # Revoke in Celery
        if execution.celery_task_id:
            from app.workers.celery_app import celery_app
            celery_app.control.revoke(execution.celery_task_id, terminate=True)

        execution.status = ExecutionStatus.CANCELLED
        execution.completed_at = datetime.now(tz=timezone.utc)
        from app.core.database import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            session.add(execution)
            await session.commit()
            await session.refresh(execution)
        return execution

    def _dispatch_to_celery(self, task: Task, execution_id: int) -> None:
        """Route the task to the correct Celery worker."""
        from app.workers.celery_app import celery_app
        task_name_map = {
            "email":        "app.tasks.email_task.send_email",
            "http":         "app.tasks.http_task.http_request",
            "file_cleanup": "app.tasks.file_cleanup_task.cleanup",
            "db_backup":    "app.tasks.db_backup_task.backup",
            "custom":       "app.tasks.custom_task.run_custom",
        }
        celery_task_name = task_name_map.get(task.task_type.value, "app.tasks.custom_task.run_custom")
        celery_app.send_task(
            celery_task_name,
            args=[execution_id, task.id, task.task_config],
            soft_time_limit=task.timeout_seconds,
            time_limit=task.timeout_seconds + 30,
        )

    async def _register_beat_schedule(self, task: Task) -> None:
        """Register or update the Celery Beat schedule for this task."""
        try:
            from celery.schedules import crontab, schedule as celery_schedule
            from redbeat import RedBeatSchedulerEntry
            from app.workers.celery_app import celery_app
            from app.core.config import get_settings
            import redis as sync_redis

            settings = get_settings()
            r = sync_redis.from_url(settings.REDIS_URL)

            task_name_map = {
                "email":        "app.tasks.email_task.send_email",
                "http":         "app.tasks.http_task.http_request",
                "file_cleanup": "app.tasks.file_cleanup_task.cleanup",
                "db_backup":    "app.tasks.db_backup_task.backup",
                "custom":       "app.tasks.custom_task.run_custom",
            }
            celery_task = task_name_map.get(task.task_type.value)

            # Build an execution record to pass id to the task
            execution = await self._exec_repo.create_execution(task.id, triggered_by="scheduler_register")

            sched_map = {
                ScheduleType.DAILY:   crontab(hour=0, minute=0),
                ScheduleType.WEEKLY:  crontab(day_of_week=1, hour=0, minute=0),
                ScheduleType.MONTHLY: crontab(day_of_month=1, hour=0, minute=0),
            }

            if task.schedule_type == ScheduleType.ONE_TIME:
                if task.scheduled_at:
                    from datetime import datetime
                    run_at = datetime.fromisoformat(task.scheduled_at.replace("Z", "+00:00"))
                    delay = (run_at - datetime.now(timezone.utc)).total_seconds()
                    if delay > 0:
                        celery_app.send_task(
                            celery_task,
                            args=[execution.id, task.id, task.task_config],
                            countdown=delay,
                        )
                return

            if task.schedule_type == ScheduleType.CRON and task.cron_expression:
                parts = task.cron_expression.strip().split()
                if len(parts) == 5:
                    minute, hour, dom, month, dow = parts
                    cron = crontab(minute=minute, hour=hour, day_of_month=dom, month_of_year=month, day_of_week=dow)
                else:
                    cron = crontab()
            else:
                cron = sched_map.get(task.schedule_type, crontab())

            entry = RedBeatSchedulerEntry(
                f"taskq:task:{task.id}",
                celery_task,
                cron,
                args=[execution.id, task.id, task.task_config],
                app=celery_app,
            )
            entry.save()
            r.close()
        except Exception as e:
            logger.warning("Failed to register beat schedule task_id=%s: %s", task.id, e)

    def _remove_beat_schedule(self, task: Task) -> None:
        try:
            from redbeat import RedBeatSchedulerEntry
            from app.workers.celery_app import celery_app
            entry = RedBeatSchedulerEntry.from_key(f"taskq:task:{task.id}", app=celery_app)
            entry.delete()
        except Exception as e:
            logger.warning("Failed to remove beat schedule task_id=%s: %s", task.id, e)
