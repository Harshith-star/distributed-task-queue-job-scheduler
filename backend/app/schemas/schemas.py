"""Schemas for executions, dashboard, analytics, notifications, audit logs."""
from datetime import datetime
from pydantic import BaseModel


# ── Execution ──────────────────────────────────────────────────────────────

class ExecutionOut(BaseModel):
    id:             int
    task_id:        int
    task_name:      str | None = None
    celery_task_id: str | None
    status:         str
    started_at:     datetime | None
    completed_at:   datetime | None
    duration_ms:    float | None
    worker_name:    str | None
    retry_count:    int
    failure_reason: str | None
    logs:           str | None
    result:         str | None
    triggered_by:   str
    created_at:     datetime

    model_config = {"from_attributes": True}


class ExecutionListResponse(BaseModel):
    items:       list[ExecutionOut]
    total:       int
    page:        int
    page_size:   int
    total_pages: int


# ── Dashboard ──────────────────────────────────────────────────────────────

class DashboardStats(BaseModel):
    total_tasks:          int
    active_tasks:         int
    paused_tasks:         int
    total_executions:     int
    running_executions:   int
    completed_executions: int
    failed_executions:    int
    queued_executions:    int
    success_rate:         float   # 0-100
    avg_duration_ms:      float
    executions_today:     int


# ── Analytics ──────────────────────────────────────────────────────────────

class DailyExecutionPoint(BaseModel):
    date:      str
    completed: int
    failed:    int
    total:     int


class AnalyticsResponse(BaseModel):
    daily_executions:     list[DailyExecutionPoint]
    task_type_breakdown:  dict[str, int]
    status_breakdown:     dict[str, int]
    avg_duration_by_type: dict[str, float]
    failure_rate_trend:   list[dict]
    top_failing_tasks:    list[dict]


# ── Notification ───────────────────────────────────────────────────────────

class NotificationOut(BaseModel):
    id:           int
    task_id:      int | None
    execution_id: int | None
    type:         str
    title:        str
    message:      str
    is_read:      bool
    created_at:   datetime

    model_config = {"from_attributes": True}


class MarkReadRequest(BaseModel):
    notification_ids: list[int]


# ── Audit Log ──────────────────────────────────────────────────────────────

class AuditLogOut(BaseModel):
    id:            int
    user_id:       int | None
    action:        str
    resource_type: str
    resource_id:   str | None
    details:       dict
    ip_address:    str | None
    created_at:    datetime

    model_config = {"from_attributes": True}


class AuditLogListResponse(BaseModel):
    items:       list[AuditLogOut]
    total:       int
    page:        int
    page_size:   int
    total_pages: int
