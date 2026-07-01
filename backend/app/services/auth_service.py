"""Auth service — business logic for authentication."""
import secrets
from datetime import timedelta, timezone, datetime

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.security import (
    create_access_token, decode_access_token,
    generate_refresh_token, hash_password, verify_password,
)
from app.exceptions.domain import (
    EmailAlreadyRegisteredError, ForbiddenError, InvalidCredentialsError,
    InvalidTokenError, UserNotFoundError,
)
from app.models.user import UserRole
from app.repositories.user_repository import UserRepository
from app.repositories.audit_notification_repository import AuditRepository

logger = get_logger(__name__)
settings = get_settings()

_REFRESH_PREFIX = "refresh:"
_BLACKLIST_PREFIX = "blacklist:"


class AuthService:
    def __init__(self, db: AsyncSession, redis: aioredis.Redis) -> None:
        self._user_repo  = UserRepository(db)
        self._audit_repo = AuditRepository(db)
        self._redis      = redis

    async def register(
        self,
        email: str,
        full_name: str,
        password: str,
        ip: str = "",
    ):
        if await self._user_repo.exists_by_email(email):
            raise EmailAlreadyRegisteredError()
        user = await self._user_repo.create_user(
            email=email,
            full_name=full_name,
            hashed_password=hash_password(password),
        )
        await self._audit_repo.log(
            action="user.register", resource_type="user",
            user_id=user.id, resource_id=str(user.id),
            details={"email": email}, ip_address=ip,
        )
        logger.info("User registered user_id=%s email=%s", user.id, email)
        return user

    async def login(self, email: str, password: str, ip: str = ""):
        user = await self._user_repo.get_by_email(email)
        if not user or not verify_password(password, user.hashed_password):
            raise InvalidCredentialsError()
        if not user.is_active:
            raise ForbiddenError("Account deactivated")

        access_token  = create_access_token(str(user.id), user.role.value)
        refresh_token = generate_refresh_token()

        ttl = settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400
        await self._redis.setex(f"{_REFRESH_PREFIX}{refresh_token}", ttl, str(user.id))

        await self._audit_repo.log(
            action="user.login", resource_type="user",
            user_id=user.id, resource_id=str(user.id),
            details={"email": email}, ip_address=ip,
        )
        logger.info("Login user_id=%s", user.id)
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        }

    async def refresh(self, refresh_token: str):
        user_id_str = await self._redis.get(f"{_REFRESH_PREFIX}{refresh_token}")
        if not user_id_str:
            raise InvalidTokenError("Refresh token expired or invalid")

        user = await self._user_repo.get_by_id(int(user_id_str))
        if not user or not user.is_active:
            raise InvalidTokenError()

        new_access  = create_access_token(str(user.id), user.role.value)
        new_refresh = generate_refresh_token()

        # Rotate refresh token
        await self._redis.delete(f"{_REFRESH_PREFIX}{refresh_token}")
        ttl = settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400
        await self._redis.setex(f"{_REFRESH_PREFIX}{new_refresh}", ttl, str(user.id))

        return {
            "access_token": new_access,
            "refresh_token": new_refresh,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        }

    async def logout(self, refresh_token: str) -> None:
        await self._redis.delete(f"{_REFRESH_PREFIX}{refresh_token}")

    async def change_password(
        self, user_id: int, current_password: str, new_password: str
    ) -> None:
        user = await self._user_repo.get_by_id(user_id)
        if not user:
            raise UserNotFoundError()
        if not verify_password(current_password, user.hashed_password):
            raise InvalidCredentialsError("Current password is incorrect")
        await self._user_repo.update_password(user, hash_password(new_password))
        logger.info("Password changed user_id=%s", user_id)

    async def update_profile(self, user_id: int, full_name: str | None, avatar_url: str | None):
        user = await self._user_repo.get_by_id(user_id)
        if not user:
            raise UserNotFoundError()
        if full_name is not None:
            user.full_name = full_name
        if avatar_url is not None:
            user.avatar_url = avatar_url
        from app.core.database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            db.add(user)
            await db.commit()
            await db.refresh(user)
        return user
