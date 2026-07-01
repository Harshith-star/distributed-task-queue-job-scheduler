"""Notification and AuditLog repositories."""
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.notification import Notification, NotificationType
from app.models.audit_log import AuditLog
from app.repositories.base import BaseRepository


class NotificationRepository(BaseRepository[Notification]):
    model = Notification

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db)

    async def create_notification(
        self,
        user_id: int,
        title: str,
        message: str,
        notif_type: NotificationType,
        task_id: int | None = None,
        execution_id: int | None = None,
    ) -> Notification:
        n = Notification(
            user_id=user_id,
            title=title,
            message=message,
            type=notif_type,
            task_id=task_id,
            execution_id=execution_id,
        )
        self._db.add(n)
        await self._db.commit()
        await self._db.refresh(n)
        return n

    async def list_for_user(
        self, user_id: int, unread_only: bool = False, skip: int = 0, limit: int = 50
    ) -> tuple[list[Notification], int]:
        filters = [Notification.user_id == user_id]
        if unread_only:
            filters.append(Notification.is_read == False)
        return await self.list_all(
            *filters, skip=skip, limit=limit,
            order_by=Notification.created_at.desc(),
        )

    async def mark_read(self, user_id: int, notification_ids: list[int]) -> None:
        await self._db.execute(
            update(Notification)
            .where(Notification.user_id == user_id, Notification.id.in_(notification_ids))
            .values(is_read=True)
        )
        await self._db.commit()

    async def count_unread(self, user_id: int) -> int:
        from sqlalchemy import func
        result = await self._db.execute(
            select(func.count(Notification.id))
            .where(Notification.user_id == user_id, Notification.is_read == False)
        )
        return result.scalar_one() or 0


class AuditRepository(BaseRepository[AuditLog]):
    model = AuditLog

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db)

    async def log(
        self,
        action: str,
        resource_type: str,
        user_id: int | None = None,
        resource_id: str | None = None,
        details: dict | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuditLog:
        entry = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id is not None else None,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self._db.add(entry)
        await self._db.commit()
        await self._db.refresh(entry)
        return entry

    async def list_for_user(
        self, user_id: int | None = None, skip: int = 0, limit: int = 50
    ) -> tuple[list[AuditLog], int]:
        filters = []
        if user_id:
            filters.append(AuditLog.user_id == user_id)
        return await self.list_all(
            *filters, skip=skip, limit=limit,
            order_by=AuditLog.created_at.desc(),
        )
