"""
app/core/security.py

Authentication utilities:
  - Password hashing using bcrypt via passlib
  - JWT access token creation and verification
  - Refresh token creation (opaque random token stored in Redis)

Why bcrypt?
  - Adaptive: work factor tunable as hardware gets faster.
  - Salted: rainbow table attacks impossible.
  - Industry standard for password storage.

Why separate access + refresh tokens?
  - Access tokens are short-lived (30 min) → limits blast radius of leakage.
  - Refresh tokens are long-lived and stored server-side → can be revoked.
"""
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings
from app.core.logging import get_logger
from app.exceptions.domain import InvalidTokenError, TokenExpiredError

logger = get_logger(__name__)
settings = get_settings()

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Token type constants used in JWT "type" claim
ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"


# ── Password ───────────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    """Return bcrypt hash of plain-text password."""
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if plain matches the bcrypt hash."""
    return _pwd_context.verify(plain, hashed)


# ── JWT ───────────────────────────────────────────────────────────────────

def create_access_token(
    subject: str,
    role: str,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """Create a signed JWT access token.

    Args:
        subject:      User ID as string.
        role:         User role ("admin" | "user").
        extra_claims: Additional claims merged into payload.

    Returns:
        Signed JWT string.
    """
    now = datetime.now(tz=timezone.utc)
    expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    payload: dict[str, Any] = {
        "sub": subject,
        "role": role,
        "type": ACCESS_TOKEN_TYPE,
        "iat": now,
        "exp": expire,
    }
    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and verify a JWT access token.

    Raises:
        TokenExpiredError: JWT exp claim has passed.
        InvalidTokenError: Signature invalid or payload malformed.
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        if payload.get("type") != ACCESS_TOKEN_TYPE:
            raise InvalidTokenError("Wrong token type")
        return payload
    except JWTError as exc:
        msg = str(exc).lower()
        if "expired" in msg:
            raise TokenExpiredError() from exc
        raise InvalidTokenError() from exc


# ── Refresh token (opaque) ────────────────────────────────────────────────

def generate_refresh_token() -> str:
    """Generate a cryptographically secure opaque refresh token.

    We use a random token (not JWT) so we can revoke it server-side
    by deleting it from Redis.
    """
    return secrets.token_urlsafe(64)
