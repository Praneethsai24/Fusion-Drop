"""
Authentication router — customer/rider signup, login, token refresh, and /me.
All DB access is async using AsyncSession.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.database.connection import get_db
from backend.models.user import User, UserRole
from backend.schemas.user import (
    CustomerSignup,
    RiderSignup,
    LoginRequest,
    TokenResponse,
    UserResponse,
    RefreshRequest,
)
from backend.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
)
from backend.core.exceptions import UnauthorizedError, BadRequestError
from backend.core.logging import get_logger
from backend.auth.jwt_handler import get_current_user

logger = get_logger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])


# ── Customer Signup ───────────────────────────────────────────────────────────

@router.post("/customer/signup", response_model=TokenResponse, status_code=201)
async def customer_signup(
    payload: CustomerSignup,
    db: AsyncSession = Depends(get_db),
):
    """Register a new customer account and return an access + refresh token pair."""
    result = await db.execute(select(User).where(User.email == payload.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        name=payload.name,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role=UserRole.customer,
        phone=getattr(payload, "phone", None),
    )
    db.add(user)
    await db.flush()   # get user.id before commit
    await db.commit()
    await db.refresh(user)

    logger.info("customer_signup", user_id=user.id, email=user.email)

    access_token = create_access_token(
        subject=user.id,
        extra_claims={"role": user.role.value},
    )
    refresh_token = create_refresh_token(subject=user.id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user_id=user.id,
        name=user.name,
        role=user.role,
    )


# ── Rider Signup ──────────────────────────────────────────────────────────────

@router.post("/rider/signup", response_model=TokenResponse, status_code=201)
async def rider_signup(
    payload: RiderSignup,
    db: AsyncSession = Depends(get_db),
):
    """Register a new rider account and return an access + refresh token pair."""
    result = await db.execute(select(User).where(User.email == payload.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        name=payload.name,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role=UserRole.rider,
        phone=getattr(payload, "phone", None),
        vehicle_type=payload.vehicle_type,
        current_lat=payload.current_lat,
        current_lng=payload.current_lng,
        is_available=True,
    )
    db.add(user)
    await db.flush()
    await db.commit()
    await db.refresh(user)

    logger.info("rider_signup", user_id=user.id, email=user.email)

    access_token = create_access_token(
        subject=user.id,
        extra_claims={"role": user.role.value},
    )
    refresh_token = create_refresh_token(subject=user.id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user_id=user.id,
        name=user.name,
        role=user.role,
    )


# ── Login ─────────────────────────────────────────────────────────────────────

@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Unified login for customers and riders.
    Returns an access token (30 min) and a refresh token (7 days).
    """
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    # Constant-time comparison even on missing user prevents timing attacks
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Contact support.",
        )

    access_token = create_access_token(
        subject=user.id,
        extra_claims={"role": user.role.value},
    )
    refresh_token = create_refresh_token(subject=user.id)

    logger.info("user_login", user_id=user.id, role=user.role.value)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user_id=user.id,
        name=user.name,
        role=user.role,
    )


# ── Token Refresh ─────────────────────────────────────────────────────────────

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    payload: RefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Exchange a valid refresh token for a new access token.
    The refresh token itself is NOT rotated (stateless implementation).
    For token rotation, store refresh tokens in Redis and invalidate on use.
    """
    token_data = decode_refresh_token(payload.refresh_token)
    user_id = int(token_data["sub"])

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise UnauthorizedError("User no longer exists.")
    if not user.is_active:
        raise UnauthorizedError("Account is deactivated.")

    new_access_token = create_access_token(
        subject=user.id,
        extra_claims={"role": user.role.value},
    )

    logger.info("token_refresh", user_id=user.id)

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=payload.refresh_token,  # return same refresh token
        user_id=user.id,
        name=user.name,
        role=user.role,
    )


# ── /me ───────────────────────────────────────────────────────────────────────

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Return the authenticated user's public profile."""
    return current_user