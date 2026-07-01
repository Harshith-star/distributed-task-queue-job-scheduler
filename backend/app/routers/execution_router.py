"""Task execution history router."""
import math
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies import get_current_user, Pagination
from app.repositories.execution_repository import ExecutionRepository
from app.repositories.task_repository import TaskRepository
from app.schemas.schemas import ExecutionListResponse, ExecutionOut
from app.services.task_service import TaskService

router = APIRouter(prefix="/executions", tags=["Executions"])

@router.get("", response_model=ExecutionListResponse)
async def list_executions(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    pagination: Pagination = Depends(),
    task_id: int | None = Query(None),
    status: str | None = Query(None),
):
    exec_repo = ExecutionRepository(db)
    if task_id:
        items, total = await exec_repo.list_for_task(task_id, pagination.skip, pagination.limit)
    else:
        task_repo = TaskRepository(db)
        tasks, _ = await task_repo.list_all(skip=0, limit=10000)
        from app.models.task import Task
        from sqlalchemy import select
        from app.core.database import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Task.id).where(Task.user_id == current_user.id))
            task_ids = [r[0] for r in result.all()]
        items, total = await exec_repo.list_for_user(task_ids, pagination.skip, pagination.limit, status)
    return ExecutionListResponse(items=items, total=total, page=pagination.page, page_size=pagination.page_size, total_pages=math.ceil(total / pagination.page_size) if total else 1)

@router.get("/{execution_id}", response_model=ExecutionOut)
async def get_execution(execution_id: int, current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    ex = await ExecutionRepository(db).get_by_id(execution_id)
    if not ex:
        from app.exceptions.domain import NotFoundError
        raise NotFoundError("Execution not found")
    return ex

@router.post("/{execution_id}/retry")
async def retry_execution(execution_id: int, current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    ex = await TaskService(db).retry_execution(execution_id, current_user.id)
    return {"execution_id": ex.id, "status": ex.status.value}

@router.post("/{execution_id}/cancel")
async def cancel_execution(execution_id: int, current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    ex = await TaskService(db).cancel_execution(execution_id, current_user.id)
    return {"execution_id": ex.id, "status": ex.status.value}
