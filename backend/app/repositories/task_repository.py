"""Task repository — queries for task management."""
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.task import Task, TaskStatus
from app.models.schedule import Schedule
from app.models.task_execution import TaskExecution, ExecutionStatus
from app.repositories.base import BaseRepository


class TaskRepository(BaseRepository[Task]):
    model = Task

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db)

    async def get_by_id_and_user(self, task_id: int, user_id: int) -> Task | None:
        result = await self._db.execute(
            select(Task)
            .where(Task.id == task_id, Task.user_id == user_id, Task.is_deleted == False)
            .options(selectinload(Task.schedule))
        )
        return result.scalar_one_or_none()

    async def get_by_id_with_schedule(self, task_id: int) -> Task | None:
        result = await self._db.execute(
            select(Task)
            .where(Task.id == task_id, Task.is_deleted == False)
            .options(selectinload(Task.schedule))
        )
        return result.scalar_one_or_none()

    async def list_for_user(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 20,
        status: str | None = None,
        task_type: str | None = None,
        search: str | None = None,
    ) -> tuple[list[Task], int]:
        filters = [Task.user_id == user_id, Task.is_deleted == False]
        if status:
            filters.append(Task.status == status)
        if task_type:
            filters.append(Task.task_type == task_type)
        if search:
            filters.append(
                or_(
                    Task.name.ilike(f"%{search}%"),
                    Task.description.ilike(f"%{search}%"),
                )
            )
        return await self.list_all(
            *filters,
            skip=skip,
            limit=limit,
            order_by=Task.created_at.desc(),
        )

    async def list_all_active(self) -> list[Task]:
        """All non-paused, non-deleted tasks (for scheduler)."""
        result = await self._db.execute(
            select(Task)
            .where(Task.status == TaskStatus.ACTIVE, Task.is_deleted == False)
            .options(selectinload(Task.schedule))
        )
        return list(result.scalars().all())

    async def soft_delete(self, task: Task) -> None:
        task.is_deleted = True
        task.status = TaskStatus.DELETED
        await self._db.commit()

    async def get_execution_counts(self, task_id: int) -> dict:
        total = (await self._db.execute(
            select(func.count(TaskExecution.id)).where(TaskExecution.task_id == task_id)
        )).scalar_one()
        success = (await self._db.execute(
            select(func.count(TaskExecution.id)).where(
                TaskExecution.task_id == task_id,
                TaskExecution.status == ExecutionStatus.COMPLETED,
            )
        )).scalar_one()
        return {"total": total or 0, "successful": success or 0}
