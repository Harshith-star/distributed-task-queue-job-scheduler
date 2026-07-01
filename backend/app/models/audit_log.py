"""AuditLog — immutable record of every state-changing action."""
from typing import TYPE_CHECKING
from sqlalchemy import ForeignKey, Index, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class AuditLog(Base, TimestampMixin):
    __tablename__ = "audit_logs"

    id:            Mapped[int]        = mapped_column(Integer, primary_key=True)
    user_id:       Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action:        Mapped[str]        = mapped_column(String(100), nullable=False)        # e.g. "task.create"
    resource_type: Mapped[str]        = mapped_column(String(50), nullable=False)         # e.g. "task"
    resource_id:   Mapped[str | None] = mapped_column(String(100), nullable=True)
    details:       Mapped[dict]       = mapped_column(JSON, default=dict, nullable=False)
    ip_address:    Mapped[str | None] = mapped_column(String(50), nullable=True)
    user_agent:    Mapped[str | None] = mapped_column(String(500), nullable=True)

    user: Mapped["User | None"] = relationship("User", back_populates="audit_logs")

    __table_args__ = (
        Index("ix_audit_user_action", "user_id", "action"),
        Index("ix_audit_resource",    "resource_type", "resource_id"),
    )

    def __repr__(self) -> str:
        return f"<AuditLog action={self.action!r} user_id={self.user_id}>"
