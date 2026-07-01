"""User model — authentication and RBAC."""
import enum
from typing import TYPE_CHECKING
from sqlalchemy import Boolean, Enum, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.task import Task
    from app.models.notification import Notification
    from app.models.audit_log import AuditLog


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    USER  = "user"


class User(Base, TimestampMixin):
    """Authenticated user with role-based access control."""
    __tablename__ = "users"

    id:             Mapped[int]    = mapped_column(Integer, primary_key=True)
    email:          Mapped[str]    = mapped_column(String(320), unique=True, nullable=False, index=True)
    full_name:      Mapped[str]    = mapped_column(String(200), nullable=False)
    hashed_password:Mapped[str]    = mapped_column(String(255), nullable=False)
    role:           Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="userrole"), default=UserRole.USER, nullable=False
    )
    is_active:      Mapped[bool]   = mapped_column(Boolean, default=True, nullable=False)
    avatar_url:     Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Relationships
    tasks:         Mapped[list["Task"]]          = relationship("Task",         back_populates="owner", cascade="all, delete-orphan")
    notifications: Mapped[list["Notification"]]  = relationship("Notification", back_populates="user",  cascade="all, delete-orphan")
    audit_logs:    Mapped[list["AuditLog"]]      = relationship("AuditLog",     back_populates="user")

    __table_args__ = (
        Index("ix_users_email_active", "email", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r} role={self.role.value}>"
