"""
FastAPI auth dependencies with role-based access control.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.database.connection import get_db
from backend.auth.jwt_handler import decode_token
from backend.models.user import User, UserRole
from backend.core.exceptions import UnauthorizedError

bearer_scheme = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    payload = decode_token(credentials.credentials, token_type="access")
    user_id = int(payload["sub"])
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise UnauthorizedError("User not found")
    return user


async def require_customer(user: User = Depends(get_current_user)) -> User:
    if user.role not in (UserRole.customer, UserRole.admin):
        raise HTTPException(status_code=403, detail="Customer access required")
    return user


async def require_rider(user: User = Depends(get_current_user)) -> User:
    if user.role not in (UserRole.rider, UserRole.admin):
        raise HTTPException(status_code=403, detail="Rider access required")
    return user


async def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user