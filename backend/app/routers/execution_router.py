"""Task execution history router."""

import math

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import Pagination, get_current_user
from app.models.task import Task
from app.repositories.execution_repository import ExecutionRepository
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
        items, total = await exec_repo.list_for_task(
            task_id,
            pagination.skip,
            pagination.limit,
        )
    else:
        result = await db.execute(
            select(Task.id).where(
                Task.user_id == current_user.id,
                Task.is_deleted == False,
            )
        )

        task_ids = [row[0] for row in result.all()]

        items, total = await exec_repo.list_for_user(
            task_ids,
            pagination.skip,
            pagination.limit,
            status,
        )

    return ExecutionListResponse(
        items=items,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        total_pages=math.ceil(total / pagination.page_size) if total else 1,
    )


@router.get("/{execution_id}", response_model=ExecutionOut)
async def get_execution(
    execution_id: int,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ex = await ExecutionRepository(db).get_by_id(execution_id)

    if not ex:
        from app.exceptions.domain import NotFoundError

        raise NotFoundError("Execution not found")

    return ex


@router.post("/{execution_id}/retry")
async def retry_execution(
    execution_id: int,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ex = await TaskService(db).retry_execution(
        execution_id,
        current_user.id,
    )

    return {
        "execution_id": ex.id,
        "status": ex.status.value,
    }


@router.post("/{execution_id}/cancel")
async def cancel_execution(
    execution_id: int,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ex = await TaskService(db).cancel_execution(
        execution_id,
        current_user.id,
    )

    return {
        "execution_id": ex.id,
        "status": ex.status.value,
    }