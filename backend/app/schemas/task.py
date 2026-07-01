"""Pydantic V2 schemas for task management."""
from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, Field, model_validator
from app.models.task import ScheduleType, TaskStatus, TaskType


class TaskConfigEmail(BaseModel):
    to_email: str
    subject:  str
    body:     str

class TaskConfigHTTP(BaseModel):
    url:     str
    method:  Literal["GET","POST","PUT","PATCH","DELETE"] = "GET"
    headers: dict[str, str] = {}
    payload: dict[str, Any] = {}
    timeout: int = 30

class TaskConfigFileCleanup(BaseModel):
    directory: str
    pattern:   str = "*"
    older_than_days: int = 30

class TaskConfigDBBackup(BaseModel):
    database_url: str
    output_path:  str
    compress:     bool = True

class TaskConfigCustom(BaseModel):
    code:    str = Field(description="Python code to execute")
    timeout: int = 60


class CreateTaskRequest(BaseModel):
    name:            str          = Field(min_length=1, max_length=200)
    description:     str | None   = None
    task_type:       TaskType
    schedule_type:   ScheduleType
    cron_expression: str | None   = None
    scheduled_at:    str | None   = None   # ISO 8601 for ONE_TIME
    task_config:     dict         = Field(default_factory=dict)
    max_retries:     int          = Field(3, ge=0, le=10)
    timeout_seconds: int          = Field(300, ge=10, le=3600)
    tags:            list[str]    = []

    @model_validator(mode="after")
    def validate_schedule(self) -> "CreateTaskRequest":
        if self.schedule_type == ScheduleType.CRON and not self.cron_expression:
            raise ValueError("cron_expression required for CRON schedule type")
        if self.schedule_type == ScheduleType.ONE_TIME and not self.scheduled_at:
            raise ValueError("scheduled_at required for ONE_TIME schedule type")
        return self


class UpdateTaskRequest(BaseModel):
    name:            str | None   = Field(None, min_length=1, max_length=200)
    description:     str | None   = None
    cron_expression: str | None   = None
    scheduled_at:    str | None   = None
    task_config:     dict | None  = None
    max_retries:     int | None   = Field(None, ge=0, le=10)
    timeout_seconds: int | None   = Field(None, ge=10, le=3600)
    tags:            list[str] | None = None


class TaskOut(BaseModel):
    id:              int
    user_id:         int
    name:            str
    description:     str | None
    task_type:       str
    status:          str
    schedule_type:   str
    cron_expression: str | None
    scheduled_at:    str | None
    task_config:     dict
    max_retries:     int
    timeout_seconds: int
    tags:            list
    created_at:      datetime
    updated_at:      datetime
    next_run_at:     datetime | None = None
    last_run_at:     datetime | None = None
    total_executions:    int = 0
    successful_executions: int = 0

    model_config = {"from_attributes": True}


class TaskListResponse(BaseModel):
    items:       list[TaskOut]
    total:       int
    page:        int
    page_size:   int
    total_pages: int
