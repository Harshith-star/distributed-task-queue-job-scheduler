"""Task model — represents a schedulable unit of work."""
import enum
from typing import TYPE_CHECKING
from sqlalchemy import (
    Boolean, Enum, ForeignKey, Index, Integer, JSON, String, Text
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.schedule import Schedule
    from app.models.task_execution import TaskExecution
    from app.models.notification import Notification


class TaskType(str, enum.Enum):
    EMAIL       = "email"
    HTTP        = "http"
    FILE_CLEANUP = "file_cleanup"
    DB_BACKUP   = "db_backup"
    CUSTOM      = "custom"


class TaskStatus(str, enum.Enum):
    ACTIVE  = "active"
    PAUSED  = "paused"
    DELETED = "deleted"


class ScheduleType(str, enum.Enum):
    ONE_TIME = "one_time"
    DAILY    = "daily"
    WEEKLY   = "weekly"
    MONTHLY  = "monthly"
    CRON     = "cron"


class Task(Base, TimestampMixin):
    """A schedulable job definition owned by a user."""
    __tablename__ = "tasks"

    id:              Mapped[int]         = mapped_column(Integer, primary_key=True)
    user_id:         Mapped[int]         = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name:            Mapped[str]         = mapped_column(String(200), nullable=False)
    description:     Mapped[str | None]  = mapped_column(Text, nullable=True)
    task_type:       Mapped[TaskType]    = mapped_column(Enum(TaskType, name="tasktype"), nullable=False)
    status:          Mapped[TaskStatus]  = mapped_column(Enum(TaskStatus, name="taskstatus"), default=TaskStatus.ACTIVE, nullable=False)
    schedule_type:   Mapped[ScheduleType]= mapped_column(Enum(ScheduleType, name="scheduletype"), nullable=False)
    cron_expression: Mapped[str | None]  = mapped_column(String(100), nullable=True)   # for CRON type
    scheduled_at:    Mapped[str | None]  = mapped_column(String(50), nullable=True)     # ISO datetime for ONE_TIME
    task_config:     Mapped[dict]        = mapped_column(JSON, default=dict, nullable=False)
    max_retries:     Mapped[int]         = mapped_column(Integer, default=3, nullable=False)
    timeout_seconds: Mapped[int]         = mapped_column(Integer, default=300, nullable=False)
    tags:            Mapped[list]        = mapped_column(JSON, default=list, nullable=False)
    is_deleted:      Mapped[bool]        = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    owner:      Mapped["User"]                   = relationship("User", back_populates="tasks")
    schedule:   Mapped["Schedule | None"]        = relationship("Schedule", back_populates="task", uselist=False, cascade="all, delete-orphan")
    executions: Mapped[list["TaskExecution"]]    = relationship("TaskExecution", back_populates="task", cascade="all, delete-orphan")
    notifications: Mapped[list["Notification"]]  = relationship("Notification", back_populates="task", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_tasks_user_status", "user_id", "status"),
        Index("ix_tasks_type",        "task_type"),
        Index("ix_tasks_is_deleted",  "is_deleted"),
    )

    def __repr__(self) -> str:
        return f"<Task id={self.id} name={self.name!r} type={self.task_type.value}>"
