"""
Rider management — list, availability toggle, GPS update.
All DB access uses AsyncSession.
"""
from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.connection import get_db
from backend.models.user import User, UserRole
from backend.schemas.user import UserResponse
from backend.auth.jwt_handler import get_current_user
from backend.core.exceptions import UnauthorizedError
from backend.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/riders", tags=["Riders"])


@router.get("/", response_model=List[UserResponse])
async def list_riders(
    available_only: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
):
    """
    List all riders.
    Pass available_only=true to return only riders who are currently on duty.
    """
    q = select(User).where(User.role == UserRole.rider)
    if available_only:
        q = q.where(User.is_available == True)
    result = await db.execute(q)
    return result.scalars().all()


@router.patch("/availability")
async def update_availability(
    available: bool,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Rider toggles their own on-duty / off-duty availability status."""
    if current_user.role != UserRole.rider:
        raise UnauthorizedError("Only riders can update availability.")

    current_user.is_available = available
    await db.commit()

    logger.info("rider_availability_updated",
                rider_id=current_user.id, available=available)
    return {"rider_id": current_user.id, "is_available": available}


@router.patch("/location")
async def update_location(
    lat: float = Query(..., ge=-90.0, le=90.0, description="Latitude"),
    lng: float = Query(..., ge=-180.0, le=180.0, description="Longitude"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Rider updates their current GPS location.
    Coordinates are validated to be within legal bounds.
    """
    if current_user.role != UserRole.rider:
        raise UnauthorizedError("Only riders can update location.")

    current_user.current_lat = lat
    current_user.current_lng = lng
    await db.commit()

    return {"rider_id": current_user.id, "lat": lat, "lng": lng}