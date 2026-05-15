"""
Auth router — /api/v1/auth
Endpoints: register, login, refresh, me
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
from backend.database.connection import get_db
from backend.models.user import User, UserRole
from backend.auth.jwt_handler import (
    hash_password, verify_password,
    create_token_pair, decode_token,
)
from backend.auth.dependencies import get_current_user
from backend.core.exceptions import BadRequestError

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])


class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/register", status_code=201)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none():
        raise BadRequestError("Email already registered")
    user = User(
        name=payload.name,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role=UserRole.customer,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    tokens = create_token_pair(user.id, user.email, user.role.value)
    return {"user": {"id": user.id, "name": user.name, "email": user.email,
                     "role": user.role.value}, **tokens}


@router.post("/login")
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    tokens = create_token_pair(user.id, user.email, user.role.value)
    return {"user": {"id": user.id, "name": user.name, "email": user.email,
                     "role": user.role.value}, **tokens}


@router.post("/refresh")
async def refresh_tokens(payload: RefreshRequest):
    data = decode_token(payload.refresh_token, token_type="refresh")
    tokens = create_token_pair(
        int(data["sub"]), data["email"], data["role"]
    )
    return tokens


@router.get("/me")
async def me(user: User = Depends(get_current_user)):
    return {"id": user.id, "name": user.name, "email": user.email,
            "role": user.role.value}