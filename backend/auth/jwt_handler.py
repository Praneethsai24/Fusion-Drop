"""
JWT handler — thin compatibility shim.

FIX: Removed `from jose import JWTError, jwt` (python-jose not installed).
     Now delegates entirely to backend.core.security which uses PyJWT.
     All routers/dependencies that import from here continue to work.
     (Blocker #2 — ImportError: No module named 'jose')
"""
# Single source of truth — re-export everything callers need
from backend.core.security import (  # noqa: F401
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    decode_access_token,
    decode_refresh_token,
)
from backend.core.config import get_settings

settings = get_settings()


def create_token_pair(user_id: int, email: str, role: str) -> dict:
    """Returns both access and refresh tokens in one call."""
    access_token = create_access_token(
        subject=user_id,
        extra_claims={"email": email, "role": role},
    )
    refresh_token = create_refresh_token(subject=user_id)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }