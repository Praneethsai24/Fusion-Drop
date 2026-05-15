"""Pydantic schemas for user authentication and profile."""
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class CustomerSignup(BaseModel):
    name:     str      = Field(..., min_length=2, max_length=120)
    email:    EmailStr
    password: str      = Field(..., min_length=8)
    phone:    Optional[str] = None


class RiderSignup(BaseModel):
    name:         str      = Field(..., min_length=2, max_length=120)
    email:        EmailStr
    password:     str      = Field(..., min_length=8)
    phone:        Optional[str] = None
    vehicle_type: Optional[str] = "bike"
    current_lat:  Optional[float] = None
    current_lng:  Optional[float] = None


class LoginRequest(BaseModel):
    email:    EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type:   str  = "bearer"
    user_id:      int
    name:         str
    role:         str


class UserResponse(BaseModel):
    id:           int
    name:         str
    email:        str
    role:         str
    phone:        Optional[str]  = None
    is_available: Optional[bool] = None
    current_lat:  Optional[float] = None
    current_lng:  Optional[float] = None
    vehicle_type: Optional[str]  = None

    model_config = {"from_attributes": True}