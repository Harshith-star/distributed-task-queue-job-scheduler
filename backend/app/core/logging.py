"""
app/core/logging.py

Structured logging setup.

Why structured logging?
  - Parseable by log aggregators (Datadog, Loki, ELK, CloudWatch).
  - Every log line is a dictionary — filterable by field.
  - Consistent format across all modules with no boilerplate.

In production: JSON format (machine-readable).
In development: coloured human-readable format.
"""
import logging
import sys
from typing import Any

from app.core.config import get_settings

_CONFIGURED = False


class _ContextFilter(logging.Filter):
    """Inject default context fields into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: A003
        if not hasattr(record, "user_id"):
            record.user_id = None  # type: ignore[attr-defined]
        if not hasattr(record, "request_id"):
            record.request_id = None  # type: ignore[attr-defined]
        return True


def configure_logging() -> None:
    """One-shot logging configuration called at app startup."""
    global _CONFIGURED
    if _CONFIGURED:
        return
    _CONFIGURED = True

    settings = get_settings()
    level = getattr(logging, settings.LOG_LEVEL, logging.INFO)

    fmt: str
    if settings.APP_ENV == "production":
        # JSON-like format parseable by log aggregators
        fmt = (
            '{"time": "%(asctime)s", "level": "%(levelname)s", '
            '"logger": "%(name)s", "msg": %(message)r, '
            '"user_id": "%(user_id)s", "request_id": "%(request_id)s"}'
        )
    else:
        fmt = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(fmt, datefmt="%Y-%m-%dT%H:%M:%S"))
    handler.addFilter(_ContextFilter())

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers = [handler]

    # Quiet noisy third-party loggers
    for noisy in ("uvicorn.access", "httpx", "httpcore", "passlib", "celery.beat"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Return a named logger.  Always use this instead of logging.getLogger()
    directly so that all loggers share the configured handler.

    Usage:
        logger = get_logger(__name__)
        logger.info("Task created task_id=%s user_id=%s", task_id, user_id)
    """
    return logging.getLogger(name)
