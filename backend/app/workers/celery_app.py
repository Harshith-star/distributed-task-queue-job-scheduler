"""
workers/celery_app.py

Central Celery application for TaskQ.
"""

from celery import Celery
from kombu import Exchange, Queue

_celery_app: Celery | None = None


def create_celery_app() -> Celery:
    from app.core.config import get_settings

    settings = get_settings()

    app = Celery(
        "taskq",
        broker=settings.CELERY_BROKER_URL,
        backend=settings.CELERY_RESULT_BACKEND,
    )

    app.conf.update(

        # ------------------------------------------------------------------
        # Serialization
        # ------------------------------------------------------------------
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],

        # ------------------------------------------------------------------
        # Time
        # ------------------------------------------------------------------
        timezone="UTC",
        enable_utc=True,

        # ------------------------------------------------------------------
        # Worker
        # ------------------------------------------------------------------
        task_track_started=True,
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        worker_prefetch_multiplier=1,

        # ------------------------------------------------------------------
        # Retry / Timeout
        # ------------------------------------------------------------------
        task_soft_time_limit=settings.CELERY_TASK_TIMEOUT,
        task_time_limit=settings.CELERY_TASK_TIMEOUT + 30,

        # ------------------------------------------------------------------
        # Results
        # ------------------------------------------------------------------
        result_expires=86400,

        # ------------------------------------------------------------------
        # Queues
        # ------------------------------------------------------------------
        task_default_queue="default",

        task_queues=(

            Queue(
                "default",
                Exchange("default"),
                routing_key="default",
            ),

            Queue(
                "email",
                Exchange("email"),
                routing_key="email",
            ),

            Queue(
                "http",
                Exchange("http"),
                routing_key="http",
            ),

            Queue(
                "maintenance",
                Exchange("maintenance"),
                routing_key="maintenance",
            ),

        ),

        task_routes={

            "app.tasks.email_task.send_email":
                {"queue": "email"},

            "app.tasks.http_task.http_request":
                {"queue": "http"},

            "app.tasks.file_cleanup_task.cleanup":
                {"queue": "maintenance"},

            "app.tasks.db_backup_task.backup":
                {"queue": "maintenance"},

            "app.tasks.custom_task.run_custom":
                {"queue": "default"},
        },

        # ------------------------------------------------------------------
        # Beat
        # ------------------------------------------------------------------
        beat_scheduler="redbeat.RedBeatScheduler",
        redbeat_redis_url=settings.REDIS_URL,
        redbeat_key_prefix="taskq:beat:",
    )

    app.autodiscover_tasks(
        [
            "app.tasks.email_task",
            "app.tasks.http_task",
            "app.tasks.file_cleanup_task",
            "app.tasks.db_backup_task",
            "app.tasks.custom_task",
        ]
    )

    return app


def get_celery() -> Celery:
    global _celery_app

    if _celery_app is None:
        _celery_app = create_celery_app()

    return _celery_app


celery_app = get_celery()


# Import signals
from app.workers import startup  # noqa