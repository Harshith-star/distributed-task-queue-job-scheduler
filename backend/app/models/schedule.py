"""Schedule model — beat schedule state per task."""
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.task import Task


class Schedule(Base, TimestampMixin):
    """Tracks scheduling metadata for each task."""
    __tablename__ = "schedules"

    id:          Mapped[int]            = mapped_column(Integer, primary_key=True)
    task_id:     Mapped[int]            = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), unique=True, nullable=False)
    next_run_at: Mapped[datetime | None]= mapped_column(DateTime(timezone=True), nullable=True, index=True)
    last_run_at: Mapped[datetime | None]= mapped_column(DateTime(timezone=True), nullable=True)
    beat_key:    Mapped[str | None]     = mapped_column(String(300), nullable=True)  # celery-redbeat schedule key

    # Relationship
    task: Mapped["Task"] = relationship("Task", back_populates="schedule")

    def __repr__(self) -> str:
        return f"<Schedule task_id={self.task_id} next_run={self.next_run_at}>"
