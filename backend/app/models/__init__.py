"""Import all models so Alembic can discover them via Base.metadata."""
from app.models.user import User, UserRole
from app.models.task import Task, TaskType, TaskStatus, ScheduleType
from app.models.schedule import Schedule
from app.models.task_execution import TaskExecution, ExecutionStatus
from app.models.notification import Notification, NotificationType
from app.models.audit_log import AuditLog

__all__ = [
    "User", "UserRole",
    "Task", "TaskType", "TaskStatus", "ScheduleType",
    "Schedule",
    "TaskExecution", "ExecutionStatus",
    "Notification", "NotificationType",
    "AuditLog",
]
