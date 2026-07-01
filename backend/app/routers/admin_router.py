"""Admin-only router."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies import get_current_admin, Pagination
from app.repositories.user_repository import UserRepository
from app.schemas.auth import UserOut

router = APIRouter(prefix="/admin", tags=["Admin"])

@router.get("/users")
async def list_users(admin=Depends(get_current_admin), db: AsyncSession = Depends(get_db), pagination: Pagination = Depends()):
    users, total = await UserRepository(db).list_users(pagination.skip, pagination.limit)
    return {"items": [UserOut.model_validate(u) for u in users], "total": total}

@router.patch("/users/{user_id}/activate")
async def toggle_user(user_id: int, active: bool, admin=Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    repo = UserRepository(db)
    user = await repo.get_by_id(user_id)
    if not user:
        from app.exceptions.domain import UserNotFoundError
        raise UserNotFoundError()
    user.is_active = active
    from app.core.database import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        session.add(user)
        await session.commit()
    return {"user_id": user_id, "is_active": active}

@router.get("/workers/status")
async def worker_status(admin=Depends(get_current_admin)):
    from app.workers.celery_app import celery_app
    inspect = celery_app.control.inspect(timeout=3)
    active  = inspect.active()  or {}
    stats   = inspect.stats()   or {}
    return {"active_tasks": active, "worker_stats": stats, "workers": list(stats.keys())}
