"""Notification model — in-app and email alerts."""
import enum
from typing import TYPE_CHECKING
from sqlalchemy import Boolean, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.task import Task


class NotificationType(str, enum.Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    RETRY   = "retry"
    INFO    = "info"


class Notification(Base, TimestampMixin):
    __tablename__ = "notifications"

    id:           Mapped[int]              = mapped_column(Integer, primary_key=True)
    user_id:      Mapped[int]              = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    task_id:      Mapped[int | None]       = mapped_column(ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True)
    execution_id: Mapped[int | None]       = mapped_column(Integer, nullable=True)
    type:         Mapped[NotificationType] = mapped_column(Enum(NotificationType, name="notiftype"), nullable=False)
    title:        Mapped[str]              = mapped_column(String(300), nullable=False)
    message:      Mapped[str]              = mapped_column(Text, nullable=False)
    is_read:      Mapped[bool]             = mapped_column(Boolean, default=False, nullable=False)

    user: Mapped["User"]        = relationship("User", back_populates="notifications")
    task: Mapped["Task | None"] = relationship("Task", back_populates="notifications")

    __table_args__ = (
        Index("ix_notifs_user_read", "user_id", "is_read"),
    )
