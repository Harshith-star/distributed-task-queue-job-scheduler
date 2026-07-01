"""Execution repository — reads and writes task execution records."""
from datetime import datetime, timezone
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.task_execution import ExecutionStatus, TaskExecution
from app.repositories.base import BaseRepository


class ExecutionRepository(BaseRepository[TaskExecution]):
    model = TaskExecution

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db)

    async def create_execution(
        self, task_id: int, triggered_by: str = "scheduler"
    ) -> TaskExecution:
        ex = TaskExecution(task_id=task_id, status=ExecutionStatus.QUEUED, triggered_by=triggered_by)
        self._db.add(ex)
        await self._db.commit()
        await self._db.refresh(ex)
        return ex

    async def list_for_task(
        self, task_id: int, skip: int = 0, limit: int = 20
    ) -> tuple[list[TaskExecution], int]:
        return await self.list_all(
            TaskExecution.task_id == task_id,
            skip=skip, limit=limit,
            order_by=TaskExecution.created_at.desc(),
        )

    async def list_for_user(
        self,
        task_ids: list[int],
        skip: int = 0,
        limit: int = 20,
        status: str | None = None,
    ) -> tuple[list[TaskExecution], int]:
        filters = [TaskExecution.task_id.in_(task_ids)]
        if status:
            filters.append(TaskExecution.status == status)
        return await self.list_all(
            *filters, skip=skip, limit=limit,
            order_by=TaskExecution.created_at.desc(),
        )

    async def get_by_celery_id(self, celery_id: str) -> TaskExecution | None:
        result = await self._db.execute(
            select(TaskExecution).where(TaskExecution.celery_task_id == celery_id)
        )
        return result.scalar_one_or_none()

    async def mark_running(self, ex: TaskExecution, worker: str, celery_id: str) -> TaskExecution:
        ex.status = ExecutionStatus.RUNNING
        ex.started_at = datetime.now(tz=timezone.utc)
        ex.worker_name = worker
        ex.celery_task_id = celery_id
        await self._db.commit()
        await self._db.refresh(ex)
        return ex

    async def mark_completed(self, ex: TaskExecution, result: str | None = None) -> TaskExecution:
        now = datetime.now(tz=timezone.utc)
        ex.status = ExecutionStatus.COMPLETED
        ex.completed_at = now
        if ex.started_at:
            ex.duration_ms = (now - ex.started_at).total_seconds() * 1000
        ex.result = result
        await self._db.commit()
        await self._db.refresh(ex)
        return ex

    async def mark_failed(
        self, ex: TaskExecution, reason: str, logs: str | None = None
    ) -> TaskExecution:
        now = datetime.now(tz=timezone.utc)
        ex.status = ExecutionStatus.FAILED
        ex.completed_at = now
        if ex.started_at:
            ex.duration_ms = (now - ex.started_at).total_seconds() * 1000
        ex.failure_reason = reason
        ex.logs = logs
        await self._db.commit()
        await self._db.refresh(ex)
        return ex

    async def mark_retrying(self, ex: TaskExecution) -> TaskExecution:
        ex.status = ExecutionStatus.RETRYING
        ex.retry_count += 1
        await self._db.commit()
        await self._db.refresh(ex)
        return ex

    async def get_stats(self, task_ids: list[int]) -> dict:
        if not task_ids:
            return {"total": 0, "running": 0, "completed": 0, "failed": 0, "queued": 0}
        rows = (await self._db.execute(
            select(TaskExecution.status, func.count(TaskExecution.id))
            .where(TaskExecution.task_id.in_(task_ids))
            .group_by(TaskExecution.status)
        )).all()
        counts = {row[0].value: row[1] for row in rows}
        total = sum(counts.values())
        return {
            "total":     total,
            "running":   counts.get("running",   0),
            "completed": counts.get("completed", 0),
            "failed":    counts.get("failed",    0),
            "queued":    counts.get("queued",    0),
        }

    async def get_avg_duration(self, task_ids: list[int]) -> float:
        if not task_ids:
            return 0.0
        result = await self._db.execute(
            select(func.avg(TaskExecution.duration_ms))
            .where(
                TaskExecution.task_id.in_(task_ids),
                TaskExecution.status == ExecutionStatus.COMPLETED,
                TaskExecution.duration_ms.isnot(None),
            )
        )
        val = result.scalar_one_or_none()
        return round(float(val), 2) if val else 0.0

    async def get_daily_counts(self, task_ids: list[int], days: int = 14) -> list[dict]:
        from sqlalchemy import cast, Date, text
        result = await self._db.execute(
            select(
                cast(TaskExecution.started_at, Date).label("date"),
                func.count(TaskExecution.id).label("total"),
                func.sum(
                    func.cast(TaskExecution.status == ExecutionStatus.COMPLETED, func.Integer if False else func.Integer)
                ).label("completed"),
            )
            .where(
                TaskExecution.task_id.in_(task_ids),
                TaskExecution.started_at.isnot(None),
                func.date(TaskExecution.started_at) >= func.current_date() - text(f"interval '{days} days'"),
            )
            .group_by(cast(TaskExecution.started_at, Date))
            .order_by(cast(TaskExecution.started_at, Date))
        )
        return [{"date": str(r.date), "total": r.total or 0, "completed": int(r.completed or 0)} for r in result]
