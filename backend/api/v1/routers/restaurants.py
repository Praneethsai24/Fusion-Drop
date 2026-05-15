"""
Restaurants router — /api/v1/restaurants
Cached responses with automatic invalidation.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from backend.database.connection import get_db
from backend.models.restaurant import Restaurant, MenuItem
from backend.services.cache import cache_get, cache_set
from backend.config import get_settings
from backend.core.logging import get_logger

router = APIRouter(prefix="/api/v1/restaurants", tags=["Restaurants"])
settings = get_settings()
logger = get_logger(__name__)


def _restaurant_to_dict(r: Restaurant) -> dict:
    return {
        "id": r.id,
        "name": r.name,
        "cuisine_type": r.cuisine_type,
        "description": r.description,
        "address": r.address,
        "lat": r.lat,
        "lng": r.lng,
        "avg_prep_time_minutes": r.avg_prep_time_minutes,
        "rating": r.rating,
        "menu": [
            {
                "id": m.id,
                "name": m.name,
                "description": m.description,
                "price": m.price,
                "category": m.category,
            }
            for m in r.menu_items
        ],
    }


@router.get("/", response_model=List[dict])
async def list_restaurants(
    cuisine: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    cache_key = f"restaurants:list:{cuisine or 'all'}:{search or 'all'}"
    cached = await cache_get(cache_key)
    if cached:
        logger.info("cache_hit", key=cache_key)
        return cached

    query = select(Restaurant).options(selectinload(Restaurant.menu_items))
    if cuisine:
        query = query.where(Restaurant.cuisine_type.ilike(f"%{cuisine}%"))
    if search:
        query = query.where(
            Restaurant.name.ilike(f"%{search}%")
            | Restaurant.description.ilike(f"%{search}%")
        )

    result = await db.execute(query)
    restaurants = result.scalars().all()
    data = [_restaurant_to_dict(r) for r in restaurants]

    await cache_set(cache_key, data, ttl=settings.CACHE_TTL_RESTAURANTS)
    return data


@router.get("/{restaurant_id}", response_model=dict)
async def get_restaurant(restaurant_id: int, db: AsyncSession = Depends(get_db)):
    cache_key = f"restaurants:detail:{restaurant_id}"
    cached = await cache_get(cache_key)
    if cached:
        return cached

    result = await db.execute(
        select(Restaurant)
        .options(selectinload(Restaurant.menu_items))
        .where(Restaurant.id == restaurant_id)
    )
    restaurant = result.scalar_one_or_none()
    if not restaurant:
        from backend.core.exceptions import NotFoundError
        raise NotFoundError("Restaurant", restaurant_id)

    data = _restaurant_to_dict(restaurant)
    await cache_set(cache_key, data, ttl=settings.CACHE_TTL_RESTAURANTS)
    return data