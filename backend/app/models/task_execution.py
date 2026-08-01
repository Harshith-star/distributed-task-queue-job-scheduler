"""TaskExecution — immutable record of every job run."""
import enum
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, Text, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.task import Task


class ExecutionStatus(str, enum.Enum):
    QUEUED    = "queued"
    RUNNING   = "running"
    COMPLETED = "completed"
    FAILED    = "failed"
    CANCELLED = "cancelled"
    RETRYING  = "retrying"


class TaskExecution(Base, TimestampMixin):
    """Immutable log of a single task execution attempt."""
    __tablename__ = "task_executions"

    id:             Mapped[int]              = mapped_column(Integer, primary_key=True)
    task_id:        Mapped[int]              = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    celery_task_id: Mapped[str | None]       = mapped_column(String(200), nullable=True, index=True)
    status:         Mapped[ExecutionStatus]  = mapped_column(
        Enum(ExecutionStatus, name="executionstatus", values_callable=lambda enum_cls: [e.value for e in enum_cls],),
        default=ExecutionStatus.QUEUED,
        nullable=False,
    )
    started_at:     Mapped[datetime | None]  = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at:   Mapped[datetime | None]  = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms:    Mapped[float | None]     = mapped_column(Float, nullable=True)
    worker_name:    Mapped[str | None]       = mapped_column(String(200), nullable=True)
    retry_count:    Mapped[int]              = mapped_column(Integer, default=0, nullable=False)
    failure_reason: Mapped[str | None]       = mapped_column(Text, nullable=True)
    logs:           Mapped[str | None]       = mapped_column(Text, nullable=True)
    result:         Mapped[str | None]       = mapped_column(Text, nullable=True)
    triggered_by:   Mapped[str]              = mapped_column(String(50), default="scheduler", nullable=False)  # scheduler | manual | retry

    # Relationship
    task: Mapped["Task"] = relationship("Task", back_populates="executions")

    __table_args__ = (
        Index("ix_executions_task_status",  "task_id", "status"),
        Index("ix_executions_status",       "status"),
        Index("ix_executions_started_at",   "started_at"),
    )

    def __repr__(self) -> str:
        return f"<TaskExecution id={self.id} task_id={self.task_id} status={self.status.value}>"
