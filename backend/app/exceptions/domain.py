"""
app/exceptions/domain.py

Custom domain exceptions.

Why custom exceptions instead of raising HTTPException in services?
  - Services should not know about HTTP — that is the router's job.
  - One global handler converts AppError → JSONResponse (DRY).
  - Meaningful names make code self-documenting.
  - Subclasses carry exactly the context needed for logging/alerting.

SOLID: Open/Closed — add new errors by subclassing, not modifying the handler.
"""
from __future__ import annotations

from typing import Any


class AppError(Exception):
    """Base class for all application domain errors.

    Attributes:
        status_code: HTTP status code returned to the client.
        detail:      Human-readable message (safe to expose publicly).
        internal:    Additional context for internal logging only.
    """

    status_code: int = 500
    detail: str = "An unexpected error occurred"

    def __init__(
        self,
        detail: str | None = None,
        internal: dict[str, Any] | None = None,
    ) -> None:
        self.detail = detail or self.__class__.detail
        self.internal = internal or {}
        super().__init__(self.detail)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(detail={self.detail!r})"


# ── 400 Bad Request ────────────────────────────────────────────────────────

class BadRequestError(AppError):
    status_code = 400
    detail = "Bad request"


class ValidationError(AppError):
    status_code = 422
    detail = "Validation failed"


# ── 401 Unauthorized ───────────────────────────────────────────────────────

class UnauthorizedError(AppError):
    status_code = 401
    detail = "Not authenticated"


class InvalidCredentialsError(AppError):
    status_code = 401
    detail = "Incorrect email or password"


class TokenExpiredError(AppError):
    status_code = 401
    detail = "Token has expired"


class InvalidTokenError(AppError):
    status_code = 401
    detail = "Invalid token"


# ── 403 Forbidden ─────────────────────────────────────────────────────────

class ForbiddenError(AppError):
    status_code = 403
    detail = "You do not have permission to perform this action"


class InsufficientRoleError(AppError):
    status_code = 403
    detail = "Admin role required"


# ── 404 Not Found ─────────────────────────────────────────────────────────

class NotFoundError(AppError):
    status_code = 404
    detail = "Resource not found"


class TaskNotFoundError(AppError):
    status_code = 404
    detail = "Task not found"


class UserNotFoundError(AppError):
    status_code = 404
    detail = "User not found"


# ── 409 Conflict ──────────────────────────────────────────────────────────

class ConflictError(AppError):
    status_code = 409
    detail = "Resource already exists"


class EmailAlreadyRegisteredError(AppError):
    status_code = 409
    detail = "Email already registered"


# ── 429 Rate Limited ──────────────────────────────────────────────────────

class RateLimitError(AppError):
    status_code = 429
    detail = "Too many requests — please slow down"


# ── 500 Server Error ──────────────────────────────────────────────────────

class WorkerError(AppError):
    status_code = 500
    detail = "Worker execution failed"


class SchedulerError(AppError):
    status_code = 500
    detail = "Scheduler error"


class EmailDeliveryError(AppError):
    status_code = 502
    detail = "Failed to send email notification"


# ── Task lifecycle ────────────────────────────────────────────────────────

class TaskAlreadyRunningError(AppError):
    status_code = 409
    detail = "Task is already running"


class TaskNotRetriableError(AppError):
    status_code = 422
    detail = "Task cannot be retried in its current state"


class TaskCannotBeCancelledError(AppError):
    status_code = 422
    detail = "Only queued or running tasks can be cancelled"
