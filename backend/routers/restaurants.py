"""
Restaurant and menu-item endpoints.
All DB access uses AsyncSession.
"""
from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.connection import get_db
from backend.models.restaurant import Restaurant, MenuItem
from backend.schemas.restaurant import (
    RestaurantCreate,
    RestaurantResponse,
    MenuItemCreate,
    MenuItemResponse,
)
from backend.core.exceptions import NotFoundError
from backend.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/restaurants", tags=["Restaurants"])


@router.post("/", response_model=RestaurantResponse, status_code=201)
async def create_restaurant(
    payload: RestaurantCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new restaurant entry (admin / seed use only)."""
    r = Restaurant(**payload.model_dump())
    db.add(r)
    await db.flush()
    await db.commit()
    await db.refresh(r)
    logger.info("restaurant_created", restaurant_id=r.id, name=r.name)
    return r


@router.get("/", response_model=List[RestaurantResponse])
async def list_restaurants(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    cuisine: str | None = Query(default=None, description="Filter by cuisine type"),
    db: AsyncSession = Depends(get_db),
):
    """
    List all open restaurants with their menus.
    Optionally filter by cuisine type (case-insensitive).
    """
    q = select(Restaurant).where(Restaurant.is_open == True)

    if cuisine:
        q = q.where(Restaurant.cuisine_type.ilike(f"%{cuisine}%"))

    q = q.offset(skip).limit(limit)
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/{restaurant_id}", response_model=RestaurantResponse)
async def get_restaurant(
    restaurant_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Fetch one restaurant with its full menu."""
    result = await db.execute(
        select(Restaurant).where(Restaurant.id == restaurant_id)
    )
    r = result.scalar_one_or_none()
    if not r:
        raise NotFoundError("Restaurant", restaurant_id)
    return r


@router.post("/{restaurant_id}/menu", response_model=MenuItemResponse, status_code=201)
async def add_menu_item(
    restaurant_id: int,
    payload: MenuItemCreate,
    db: AsyncSession = Depends(get_db),
):
    """Add a new menu item to a restaurant."""
    result = await db.execute(
        select(Restaurant).where(Restaurant.id == restaurant_id)
    )
    if not result.scalar_one_or_none():
        raise NotFoundError("Restaurant", restaurant_id)

    item = MenuItem(restaurant_id=restaurant_id, **payload.model_dump())
    db.add(item)
    await db.flush()
    await db.commit()
    await db.refresh(item)
    logger.info("menu_item_added", restaurant_id=restaurant_id, item_id=item.id)
    return item


@router.patch("/menu/{item_id}/availability")
async def toggle_menu_item_availability(
    item_id: int,
    available: bool,
    db: AsyncSession = Depends(get_db),
):
    """Toggle a menu item's availability (e.g. mark as sold out)."""
    result = await db.execute(select(MenuItem).where(MenuItem.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise NotFoundError("MenuItem", item_id)

    item.is_available = available
    await db.commit()
    logger.info("menu_item_toggled", item_id=item_id, available=available)
    return {"id": item_id, "is_available": available}