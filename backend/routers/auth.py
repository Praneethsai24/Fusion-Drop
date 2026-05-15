"""Authentication router — customer/rider signup and unified login."""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database.connection import get_db
from backend.models.user import User, UserRole
from backend.schemas.user import (
    CustomerSignup, RiderSignup, LoginRequest,
    TokenResponse, UserResponse,
)
from backend.auth.jwt_handler import (
    hash_password, verify_password,
    create_access_token, get_current_user,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/customer/signup", response_model=TokenResponse, status_code=201)
def customer_signup(payload: CustomerSignup, db: Session = Depends(get_db)):
    """Register a new customer account and return a JWT."""
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=409, detail="Email already registered")
    user = User(
        name=payload.name,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role=UserRole.customer,
        phone=payload.phone,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info(f"New customer: {user.email}")
    token = create_access_token({"sub": str(user.id), "role": user.role})
    return TokenResponse(access_token=token, user_id=user.id, name=user.name, role=user.role)


@router.post("/rider/signup", response_model=TokenResponse, status_code=201)
def rider_signup(payload: RiderSignup, db: Session = Depends(get_db)):
    """Register a new rider account and return a JWT."""
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=409, detail="Email already registered")
    user = User(
        name=payload.name,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role=UserRole.rider,
        phone=payload.phone,
        vehicle_type=payload.vehicle_type,
        current_lat=payload.current_lat,
        current_lng=payload.current_lng,
        is_available=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info(f"New rider: {user.email}")
    token = create_access_token({"sub": str(user.id), "role": user.role})
    return TokenResponse(access_token=token, user_id=user.id, name=user.name, role=user.role)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """Login for customers and riders. Returns a JWT."""
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account deactivated")
    token = create_access_token({"sub": str(user.id), "role": user.role})
    logger.info(f"Login: {user.email} ({user.role})")
    return TokenResponse(access_token=token, user_id=user.id, name=user.name, role=user.role)


@router.get("/me", response_model=UserResponse)
def get_me(current_user=Depends(get_current_user)):
    """Return the authenticated user's profile."""
    return current_user