"""Rider management — list, availability toggle, GPS update."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database.connection import get_db
from backend.models.user import User, UserRole
from backend.schemas.user import UserResponse
from backend.auth.jwt_handler import get_current_user

router = APIRouter(prefix="/riders", tags=["Riders"])


@router.get("/", response_model=List[UserResponse])
def list_riders(
    available_only: bool = False,
    db: Session = Depends(get_db),
):
    """List all riders; filter by availability when available_only=true."""
    q = db.query(User).filter(User.role == UserRole.rider)
    if available_only:
        q = q.filter(User.is_available == True)
    return q.all()


@router.patch("/availability")
def update_availability(
    available: bool,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Rider toggles their own availability status."""
    if current_user.role != UserRole.rider:
        raise HTTPException(status_code=403, detail="Only riders can update availability")
    current_user.is_available = available
    db.commit()
    return {"rider_id": current_user.id, "is_available": available}


@router.patch("/location")
def update_location(
    lat: float,
    lng: float,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Rider updates their current GPS location."""
    if current_user.role != UserRole.rider:
        raise HTTPException(status_code=403, detail="Only riders can update location")
    current_user.current_lat = lat
    current_user.current_lng = lng
    db.commit()
    return {"rider_id": current_user.id, "lat": lat, "lng": lng}