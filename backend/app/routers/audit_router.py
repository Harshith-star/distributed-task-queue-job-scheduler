"""Audit log router."""
import math
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies import get_current_user, get_current_admin, Pagination
from app.repositories.audit_notification_repository import AuditRepository, NotificationRepository
from app.schemas.schemas import AuditLogListResponse, NotificationOut, MarkReadRequest

router = APIRouter(prefix="/audit", tags=["Audit & Notifications"])

@router.get("/logs", response_model=AuditLogListResponse)
async def get_audit_logs(current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db), pagination: Pagination = Depends()):
    from app.models.user import UserRole
    user_id = None if current_user.role == UserRole.ADMIN else current_user.id
    items, total = await AuditRepository(db).list_for_user(user_id, pagination.skip, pagination.limit)
    return AuditLogListResponse(items=items, total=total, page=pagination.page, page_size=pagination.page_size, total_pages=math.ceil(total/pagination.page_size) if total else 1)

@router.get("/notifications")
async def get_notifications(current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db), unread_only: bool = Query(False), pagination: Pagination = Depends()):
    items, total = await NotificationRepository(db).list_for_user(current_user.id, unread_only, pagination.skip, pagination.limit)
    unread_count = await NotificationRepository(db).count_unread(current_user.id)
    return {"items": [NotificationOut.model_validate(n) for n in items], "total": total, "unread_count": unread_count}

@router.post("/notifications/read", status_code=204)
async def mark_read(payload: MarkReadRequest, current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await NotificationRepository(db).mark_read(current_user.id, payload.notification_ids)
