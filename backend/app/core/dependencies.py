"""
app/core/dependencies.py

FastAPI dependency functions — injected into routers via Depends().

Why this pattern?
  - Keeps routers thin: routers only define endpoints, not auth logic.
  - Testable: replace dependencies in tests via app.dependency_overrides.
  - Composable: RequireAdmin = Depends(get_current_user) + role check.
"""
from typing import Annotated

import redis.asyncio as aioredis
from fastapi import Depends, Header, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import get_logger
from app.core.redis import get_redis
from app.core.security import decode_access_token
from app.exceptions.domain import (
    ForbiddenError,
    InsufficientRoleError,
    RateLimitError,
    UnauthorizedError,
)

logger = get_logger(__name__)

_bearer_scheme = HTTPBearer(auto_error=False)


# ── Auth dependency ────────────────────────────────────────────────────────

async def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)
    ] = None,
    db: AsyncSession = Depends(get_db),
) -> "UserModel":  # type: ignore[name-defined]  # imported lazily below
    """Decode JWT and return the authenticated User ORM object.

    Lazy import of UserModel to avoid circular imports at module load time.
    """
    from app.repositories.user_repository import UserRepository

    if not credentials:
        raise UnauthorizedError("Authorization header missing")

    payload = decode_access_token(credentials.credentials)
    user_id: str | None = payload.get("sub")
    if not user_id:
        raise UnauthorizedError()

    user = await UserRepository(db).get_by_id(int(user_id))
    if user is None:
        raise UnauthorizedError("User account not found")
    if not user.is_active:
        raise ForbiddenError("Account is deactivated")

    return user


async def get_current_admin(
    current_user: Annotated[object, Depends(get_current_user)],
) -> "UserModel":  # type: ignore[name-defined]
    """Extends get_current_user — additionally requires admin role.

    Usage:
        @router.get("/admin-only")
        async def admin_endpoint(admin = Depends(get_current_admin)):
            ...
    """
    if current_user.role != "admin":  # type: ignore[attr-defined]
        raise InsufficientRoleError()
    return current_user  # type: ignore[return-value]


# ── Rate limiting ─────────────────────────────────────────────────────────

async def rate_limit(
    current_user: Annotated[object, Depends(get_current_user)],
    redis: aioredis.Redis = Depends(get_redis),
) -> None:
    """Sliding-window rate limiter: N requests per minute per user.

    Uses Redis INCR + EXPIRE for atomicity.
    Admins are exempt from rate limiting.
    """
    from app.core.config import get_settings

    user = current_user  # type: ignore[assignment]
    if getattr(user, "role", None) == "admin":
        return  # admins bypass rate limit

    settings = get_settings()
    key = f"rate_limit:user:{user.id}:minute"  # type: ignore[attr-defined]
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, 60)
    if count > settings.RATE_LIMIT_PER_MINUTE:
        raise RateLimitError()


# ── Pagination ────────────────────────────────────────────────────────────

class Pagination:
    """Query parameter holder for list endpoints.

    Usage:
        @router.get("/tasks")
        async def list_tasks(pagination: Pagination = Depends()):
            skip = pagination.skip
            limit = pagination.limit
    """

    def __init__(
        self,
        page: int = Query(1, ge=1, description="Page number (1-indexed)"),
        page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    ) -> None:
        self.page = page
        self.page_size = page_size

    @property
    def skip(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size
