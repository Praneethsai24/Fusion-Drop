"""
FusionDrop — Centralised security utilities.

Provides password hashing, JWT creation/decoding, and auth guard helpers.
All auth logic should import from here; auth/jwt_handler.py should
re-export from this module to maintain backward compatibility.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
from passlib.context import CryptContext

from backend.core.config import get_settings
from backend.core.exceptions import UnauthorizedError

settings = get_settings()

# bcrypt context — auto-rehashes outdated rounds on verify
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ── Password helpers ──────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    """Return a bcrypt hash of *plain*."""
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if *plain* matches *hashed*."""
    return _pwd_context.verify(plain, hashed)


# ── Token creation ────────────────────────────────────────────────────────────

def create_access_token(
    subject: str | int,
    extra_claims: Optional[dict] = None,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a signed JWT access token.

    Args:
        subject:      The token subject — typically a user's integer ID.
        extra_claims: Optional additional claims merged into the payload
                      (e.g. {"role": "rider"}).
        expires_delta: Override the default expiry from settings.
    """
    expire = datetime.now(timezone.utc) + (
        expires_delta
        or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload: dict = {"sub": str(subject), "exp": expire, "type": "access"}
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(subject: str | int) -> str:
    """
    Create a long-lived refresh token.

    Refresh tokens carry a "type": "refresh" claim so they can be
    distinguished from access tokens and rejected at protected endpoints.
    """
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    payload = {"sub": str(subject), "exp": expire, "type": "refresh"}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


# ── Token decoding ────────────────────────────────────────────────────────────

def decode_token(token: str) -> dict:
    """
    Decode and validate a JWT.

    Raises:
        UnauthorizedError: on invalid signature, expiry, or malformed token.
    """
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except ExpiredSignatureError:
        raise UnauthorizedError("Token has expired — please log in again.")
    except InvalidTokenError as exc:
        raise UnauthorizedError(f"Invalid token: {exc}") from exc


def decode_access_token(token: str) -> dict:
    """
    Like decode_token but additionally enforces type == 'access'.
    Use this at protected HTTP endpoints.
    """
    payload = decode_token(token)
    if payload.get("type") != "access":
        raise UnauthorizedError("Expected an access token.")
    return payload


def decode_refresh_token(token: str) -> dict:
    """
    Like decode_token but additionally enforces type == 'refresh'.
    Use this at the /auth/refresh endpoint.
    """
    payload = decode_token(token)
    if payload.get("type") != "refresh":
        raise UnauthorizedError("Expected a refresh token.")
    return payload