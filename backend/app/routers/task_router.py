"""Task CRUD router."""
import math
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies import get_current_user, Pagination
from app.repositories.task_repository import TaskRepository
from app.repositories.execution_repository import ExecutionRepository
from app.schemas.task import CreateTaskRequest, TaskListResponse, TaskOut, UpdateTaskRequest
from app.services.task_service import TaskService

router = APIRouter(prefix="/tasks", tags=["Tasks"])

@router.post("", response_model=TaskOut, status_code=201)
async def create_task(payload: CreateTaskRequest, request: Request, current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await TaskService(db).create_task(current_user.id, payload.model_dump(), ip=request.client.host if request.client else "")

@router.get("", response_model=TaskListResponse)
async def list_tasks(current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db), pagination: Pagination = Depends(), status: str | None = Query(None), task_type: str | None = Query(None), search: str | None = Query(None)):
    repo = TaskRepository(db)
    items, total = await repo.list_for_user(user_id=current_user.id, skip=pagination.skip, limit=pagination.limit, status=status, task_type=task_type, search=search)
    enriched = []
    exec_repo = ExecutionRepository(db)
    for task in items:
        counts = await repo.get_execution_counts(task.id)
        d = TaskOut.model_validate(task)
        d.total_executions = counts["total"]
        d.successful_executions = counts["successful"]
        if hasattr(task, "schedule") and task.schedule:
            d.next_run_at = task.schedule.next_run_at
            d.last_run_at = task.schedule.last_run_at
        enriched.append(d)
    return TaskListResponse(items=enriched, total=total, page=pagination.page, page_size=pagination.page_size, total_pages=math.ceil(total/pagination.page_size) if total else 1)

@router.get("/{task_id}", response_model=TaskOut)
async def get_task(task_id: int, current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    repo = TaskRepository(db)
    task = await repo.get_by_id_and_user(task_id, current_user.id)
    if not task:
        from app.exceptions.domain import TaskNotFoundError
        raise TaskNotFoundError()
    counts = await repo.get_execution_counts(task.id)
    d = TaskOut.model_validate(task)
    d.total_executions = counts["total"]
    d.successful_executions = counts["successful"]
    return d

@router.put("/{task_id}", response_model=TaskOut)
async def update_task(task_id: int, payload: UpdateTaskRequest, request: Request, current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    data = {k: v for k, v in payload.model_dump().items() if v is not None}
    return await TaskService(db).update_task(task_id, current_user.id, data, ip=request.client.host if request.client else "")

@router.delete("/{task_id}", status_code=204)
async def delete_task(task_id: int, request: Request, current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await TaskService(db).delete_task(task_id, current_user.id, ip=request.client.host if request.client else "")

@router.post("/{task_id}/pause", response_model=TaskOut)
async def pause_task(task_id: int, current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await TaskService(db).pause_task(task_id, current_user.id)

@router.post("/{task_id}/resume", response_model=TaskOut)
async def resume_task(task_id: int, current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await TaskService(db).resume_task(task_id, current_user.id)

@router.post("/{task_id}/trigger")
async def trigger_now(task_id: int, current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    ex = await TaskService(db).trigger_now(task_id, current_user.id)
    return {"execution_id": ex.id, "status": ex.status.value, "message": "Task queued for immediate execution"}
