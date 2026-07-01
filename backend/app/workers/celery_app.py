"""
workers/celery_app.py

Celery application setup.

Why a factory function?
  - Avoids importing settings at module load (workers may be started before .env is loaded).
  - Allows the main FastAPI app to share the same Celery instance.
"""
import os
from celery import Celery
from celery.signals import worker_ready, task_prerun, task_postrun, task_failure, task_retry

_celery_app: Celery | None = None


def create_celery_app() -> Celery:
    """Create and configure the Celery application."""
    from app.core.config import get_settings
    settings = get_settings()

    app = Celery(
        "taskq",
        broker=settings.CELERY_BROKER_URL,
        backend=settings.CELERY_RESULT_BACKEND,
    )

    app.conf.update(
        # Serialisation
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],

        # Timezone
        timezone="UTC",
        enable_utc=True,

        # Retry / acknowledgement
        task_acks_late=True,            # ack after task completes, not before
        task_reject_on_worker_lost=True,# requeue if worker dies mid-task
        task_track_started=True,

        # Timeouts
        task_soft_time_limit=settings.CELERY_TASK_TIMEOUT,
        task_time_limit=settings.CELERY_TASK_TIMEOUT + 30,

        # Result TTL
        result_expires=86400,           # 24 hours

        # Worker concurrency
        worker_prefetch_multiplier=1,   # fair distribution across workers

        # Task routing
        task_routes={
            "app.tasks.email_task.*":        {"queue": "email"},
            "app.tasks.http_task.*":         {"queue": "http"},
            "app.tasks.file_cleanup_task.*": {"queue": "maintenance"},
            "app.tasks.db_backup_task.*":    {"queue": "maintenance"},
            "app.tasks.custom_task.*":       {"queue": "default"},
        },
        task_default_queue="default",
        task_queues={
            "default":     {"exchange": "default",     "routing_key": "default"},
            "email":       {"exchange": "email",       "routing_key": "email"},
            "http":        {"exchange": "http",        "routing_key": "http"},
            "maintenance": {"exchange": "maintenance", "routing_key": "maintenance"},
        },

        # Beat scheduler uses celery-redbeat (Redis-backed)
        beat_scheduler="redbeat.RedBeatScheduler",
        redbeat_redis_url=settings.REDIS_URL,
        redbeat_key_prefix="taskq:beat:",
    )

    # Auto-discover all task modules
    app.autodiscover_tasks(
        ["app.tasks.email_task", "app.tasks.http_task",
         "app.tasks.file_cleanup_task", "app.tasks.db_backup_task",
         "app.tasks.custom_task"]
    )

    return app


def get_celery() -> Celery:
    global _celery_app
    if _celery_app is None:
        _celery_app = create_celery_app()
    return _celery_app


# Module-level singleton used by task decorators and the FastAPI app
celery_app: Celery = get_celery()

# Import startup signals so demo seeding runs when the worker connects
from app.workers import startup  # noqa: F401, E402
