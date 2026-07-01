"""Dashboard and Analytics services."""
import json
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis

from app.core.config import get_settings
from app.core.logging import get_logger
from app.repositories.task_repository import TaskRepository
from app.repositories.execution_repository import ExecutionRepository

logger = get_logger(__name__)
settings = get_settings()


class DashboardService:
    """Aggregates dashboard statistics, cached in Redis."""

    def __init__(self, db: AsyncSession, redis: aioredis.Redis) -> None:
        self._task_repo  = TaskRepository(db)
        self._exec_repo  = ExecutionRepository(db)
        self._redis      = redis

    async def get_stats(self, user_id: int) -> dict:
        cache_key = f"dashboard:stats:{user_id}"
        cached = await self._redis.get(cache_key)
        if cached:
            return json.loads(cached)

        # Fetch task IDs for this user
        tasks, _ = await self._task_repo.list_all(
            skip=0, limit=10000,
        )
        # Filter to user
        from app.models.task import Task, TaskStatus
        from sqlalchemy import select, func
        from app.core.database import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Task.id, Task.status).where(Task.user_id == user_id, Task.is_deleted == False)
            )
            rows = result.all()

        task_ids    = [r[0] for r in rows]
        active_cnt  = sum(1 for r in rows if r[1].value == "active")
        paused_cnt  = sum(1 for r in rows if r[1].value == "paused")

        exec_stats  = await self._exec_repo.get_stats(task_ids) if task_ids else {}
        avg_dur     = await self._exec_repo.get_avg_duration(task_ids) if task_ids else 0.0

        total_done = exec_stats.get("completed", 0) + exec_stats.get("failed", 0)
        success_rate = round(exec_stats.get("completed", 0) / total_done * 100, 1) if total_done > 0 else 0.0

        # Executions today
        from sqlalchemy import func, cast, Date, text
        async with AsyncSessionLocal() as session:
            from app.models.task_execution import TaskExecution
            today_result = await session.execute(
                select(func.count(TaskExecution.id)).where(
                    TaskExecution.task_id.in_(task_ids),
                    func.date(TaskExecution.created_at) == func.current_date(),
                )
            )
            executions_today = today_result.scalar_one() or 0

        stats = {
            "total_tasks":          len(task_ids),
            "active_tasks":         active_cnt,
            "paused_tasks":         paused_cnt,
            "total_executions":     exec_stats.get("total", 0),
            "running_executions":   exec_stats.get("running", 0),
            "completed_executions": exec_stats.get("completed", 0),
            "failed_executions":    exec_stats.get("failed", 0),
            "queued_executions":    exec_stats.get("queued", 0),
            "success_rate":         success_rate,
            "avg_duration_ms":      avg_dur,
            "executions_today":     executions_today,
        }

        await self._redis.setex(cache_key, settings.DASHBOARD_CACHE_TTL, json.dumps(stats))
        return stats


class AnalyticsService:
    """Deeper analytics — trends, breakdowns, failure analysis."""

    def __init__(self, db: AsyncSession) -> None:
        self._task_repo = TaskRepository(db)
        self._exec_repo = ExecutionRepository(db)

    async def get_analytics(self, user_id: int, days: int = 14) -> dict:
        from app.models.task import Task
        from app.models.task_execution import TaskExecution, ExecutionStatus
        from sqlalchemy import select, func, cast, Date
        from app.core.database import AsyncSessionLocal

        async with AsyncSessionLocal() as session:
            task_rows = (await session.execute(
                select(Task.id, Task.task_type).where(Task.user_id == user_id, Task.is_deleted == False)
            )).all()

        task_ids = [r[0] for r in task_rows]
        if not task_ids:
            return {
                "daily_executions": [], "task_type_breakdown": {},
                "status_breakdown": {}, "avg_duration_by_type": {},
                "failure_rate_trend": [], "top_failing_tasks": [],
            }

        async with AsyncSessionLocal() as session:
            # Daily counts
            from sqlalchemy import text
            daily = (await session.execute(
                select(
                    cast(TaskExecution.started_at, Date).label("date"),
                    func.count(TaskExecution.id).label("total"),
                    func.sum(
                        func.case((TaskExecution.status == ExecutionStatus.COMPLETED, 1), else_=0)
                    ).label("completed"),
                    func.sum(
                        func.case((TaskExecution.status == ExecutionStatus.FAILED, 1), else_=0)
                    ).label("failed"),
                )
                .where(
                    TaskExecution.task_id.in_(task_ids),
                    TaskExecution.started_at.isnot(None),
                    TaskExecution.started_at >= text(f"NOW() - INTERVAL '{days} days'"),
                )
                .group_by(cast(TaskExecution.started_at, Date))
                .order_by(cast(TaskExecution.started_at, Date))
            )).all()

            # Status breakdown
            status_rows = (await session.execute(
                select(TaskExecution.status, func.count(TaskExecution.id))
                .where(TaskExecution.task_id.in_(task_ids))
                .group_by(TaskExecution.status)
            )).all()

            # Top failing tasks
            fail_rows = (await session.execute(
                select(Task.id, Task.name, func.count(TaskExecution.id).label("fail_count"))
                .join(TaskExecution, Task.id == TaskExecution.task_id)
                .where(
                    Task.user_id == user_id,
                    TaskExecution.status == ExecutionStatus.FAILED,
                )
                .group_by(Task.id, Task.name)
                .order_by(func.count(TaskExecution.id).desc())
                .limit(5)
            )).all()

        type_counts = {}
        for r in task_rows:
            t = r[1].value
            type_counts[t] = type_counts.get(t, 0) + 1

        return {
            "daily_executions": [
                {"date": str(r.date), "total": r.total, "completed": int(r.completed or 0), "failed": int(r.failed or 0)}
                for r in daily
            ],
            "task_type_breakdown": type_counts,
            "status_breakdown": {r[0].value: r[1] for r in status_rows},
            "avg_duration_by_type": {},
            "failure_rate_trend": [],
            "top_failing_tasks": [
                {"task_id": r.id, "name": r.name, "fail_count": r.fail_count}
                for r in fail_rows
            ],
        }
