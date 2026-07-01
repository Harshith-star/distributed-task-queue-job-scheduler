"""Initial schema: users, tasks, schedules, task_executions, notifications, audit_logs

Revision ID: 6d496929a9e4
Revises:
Create Date: 2026-07-01
"""
from alembic import op
import sqlalchemy as sa

revision = "6d496929a9e4"
down_revision = None
branch_labels = None
depends_on = None

_user_role     = sa.Enum("admin",    "user",          name="userrole")
_task_type     = sa.Enum("email",    "http",    "file_cleanup", "db_backup", "custom", name="tasktype")
_task_status   = sa.Enum("active",   "paused",  "deleted",      name="taskstatus")
_sched_type    = sa.Enum("one_time", "daily",   "weekly", "monthly", "cron", name="scheduletype")
_exec_status   = sa.Enum("queued",   "running", "completed", "failed", "cancelled", "retrying", name="executionstatus")
_notif_type    = sa.Enum("success",  "failure", "retry", "info", name="notiftype")


def upgrade() -> None:
    op.create_table("users",
        sa.Column("id",              sa.Integer(),     primary_key=True),
        sa.Column("email",           sa.String(320),   nullable=False, unique=True),
        sa.Column("full_name",       sa.String(200),   nullable=False),
        sa.Column("hashed_password", sa.String(255),   nullable=False),
        sa.Column("role",            _user_role,       nullable=False, server_default="user"),
        sa.Column("is_active",       sa.Boolean(),     nullable=False, server_default="true"),
        sa.Column("avatar_url",      sa.String(500),   nullable=True),
        sa.Column("created_at",      sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at",      sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_email",        "users", ["email"])
    op.create_index("ix_users_email_active", "users", ["email", "is_active"])

    op.create_table("tasks",
        sa.Column("id",              sa.Integer(),    primary_key=True),
        sa.Column("user_id",         sa.Integer(),    sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name",            sa.String(200),  nullable=False),
        sa.Column("description",     sa.Text(),       nullable=True),
        sa.Column("task_type",       _task_type,      nullable=False),
        sa.Column("status",          _task_status,    nullable=False, server_default="active"),
        sa.Column("schedule_type",   _sched_type,     nullable=False),
        sa.Column("cron_expression", sa.String(100),  nullable=True),
        sa.Column("scheduled_at",    sa.String(50),   nullable=True),
        sa.Column("task_config",     sa.JSON(),       nullable=False, server_default="{}"),
        sa.Column("max_retries",     sa.Integer(),    nullable=False, server_default="3"),
        sa.Column("timeout_seconds", sa.Integer(),    nullable=False, server_default="300"),
        sa.Column("tags",            sa.JSON(),       nullable=False, server_default="[]"),
        sa.Column("is_deleted",      sa.Boolean(),    nullable=False, server_default="false"),
        sa.Column("created_at",      sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at",      sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_tasks_user_status", "tasks", ["user_id", "status"])
    op.create_index("ix_tasks_type",        "tasks", ["task_type"])
    op.create_index("ix_tasks_is_deleted",  "tasks", ["is_deleted"])

    op.create_table("schedules",
        sa.Column("id",          sa.Integer(), primary_key=True),
        sa.Column("task_id",     sa.Integer(), sa.ForeignKey("tasks.id", ondelete="CASCADE"), unique=True, nullable=False),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("beat_key",    sa.String(300), nullable=True),
        sa.Column("created_at",  sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at",  sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_schedules_next_run", "schedules", ["next_run_at"])

    op.create_table("task_executions",
        sa.Column("id",             sa.Integer(),  primary_key=True),
        sa.Column("task_id",        sa.Integer(),  sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("celery_task_id", sa.String(200), nullable=True),
        sa.Column("status",         _exec_status,  nullable=False, server_default="queued"),
        sa.Column("started_at",     sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at",   sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms",    sa.Float(),    nullable=True),
        sa.Column("worker_name",    sa.String(200), nullable=True),
        sa.Column("retry_count",    sa.Integer(),  nullable=False, server_default="0"),
        sa.Column("failure_reason", sa.Text(),     nullable=True),
        sa.Column("logs",           sa.Text(),     nullable=True),
        sa.Column("result",         sa.Text(),     nullable=True),
        sa.Column("triggered_by",   sa.String(50), nullable=False, server_default="scheduler"),
        sa.Column("created_at",     sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at",     sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_executions_task_status",  "task_executions", ["task_id", "status"])
    op.create_index("ix_executions_status",       "task_executions", ["status"])
    op.create_index("ix_executions_celery_id",    "task_executions", ["celery_task_id"])
    op.create_index("ix_executions_started_at",   "task_executions", ["started_at"])

    op.create_table("notifications",
        sa.Column("id",           sa.Integer(), primary_key=True),
        sa.Column("user_id",      sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("task_id",      sa.Integer(), sa.ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True),
        sa.Column("execution_id", sa.Integer(), nullable=True),
        sa.Column("type",         _notif_type,  nullable=False),
        sa.Column("title",        sa.String(300), nullable=False),
        sa.Column("message",      sa.Text(),    nullable=False),
        sa.Column("is_read",      sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at",   sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at",   sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_notifs_user_read", "notifications", ["user_id", "is_read"])

    op.create_table("audit_logs",
        sa.Column("id",            sa.Integer(), primary_key=True),
        sa.Column("user_id",       sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action",        sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(50),  nullable=False),
        sa.Column("resource_id",   sa.String(100), nullable=True),
        sa.Column("details",       sa.JSON(),      nullable=False, server_default="{}"),
        sa.Column("ip_address",    sa.String(50),  nullable=True),
        sa.Column("user_agent",    sa.String(500), nullable=True),
        sa.Column("created_at",    sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at",    sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_audit_user_action", "audit_logs", ["user_id", "action"])
    op.create_index("ix_audit_resource",    "audit_logs", ["resource_type", "resource_id"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("notifications")
    op.drop_table("task_executions")
    op.drop_table("schedules")
    op.drop_table("tasks")
    op.drop_table("users")
    for e in (_notif_type, _exec_status, _sched_type, _task_status, _task_type, _user_role):
        e.drop(op.get_bind(), checkfirst=True)
