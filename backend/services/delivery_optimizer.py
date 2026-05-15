"""
Delivery Optimizer Service — Async upgrade.
All original Haversine/batching logic is 100% preserved.
Only change: Session → AsyncSession + await queries.
"""
import math
import logging
from typing import List, Optional, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371.0
    φ1, φ2 = math.radians(lat1), math.radians(lat2)
    Δφ = math.radians(lat2 - lat1)
    Δλ = math.radians(lng2 - lng1)
    a = math.sin(Δφ / 2) ** 2 + math.cos(φ1) * math.cos(φ2) * math.sin(Δλ / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _centroid(coords: List[tuple]) -> tuple:
    if not coords:
        return (12.9716, 77.5946)
    return (
        sum(c[0] for c in coords) / len(coords),
        sum(c[1] for c in coords) / len(coords),
    )


def _travel_minutes(distance_km: float) -> float:
    return (distance_km / settings.AVG_RIDER_SPEED_KMH) * 60


async def optimize_delivery(
    db: AsyncSession,
    menu_item_ids: List[int],
    delivery_lat: Optional[float],
    delivery_lng: Optional[float],
) -> Dict[str, Any]:
    from backend.models.restaurant import MenuItem, Restaurant
    from backend.models.user import User, UserRole

    # 1. Gather unique restaurants
    items_result = await db.execute(
        select(MenuItem).where(MenuItem.id.in_(menu_item_ids))
    )
    items = items_result.scalars().all()
    restaurant_ids = list({i.restaurant_id for i in items})

    restaurants_result = await db.execute(
        select(Restaurant).where(Restaurant.id.in_(restaurant_ids))
    )
    restaurants = restaurants_result.scalars().all()

    if not restaurants:
        return _fallback_result()

    # 2. Pairwise distance check
    can_batch = True
    max_inter_restaurant_km = 0.0
    for i in range(len(restaurants)):
        for j in range(i + 1, len(restaurants)):
            d = _haversine_km(
                restaurants[i].lat, restaurants[i].lng,
                restaurants[j].lat, restaurants[j].lng,
            )
            max_inter_restaurant_km = max(max_inter_restaurant_km, d)
            if d > settings.BATCH_RADIUS_KM:
                can_batch = False

    logger.info(
        f"Delivery optimisation: {len(restaurants)} restaurant(s), "
        f"max inter-restaurant distance {max_inter_restaurant_km:.2f} km, "
        f"can_batch={can_batch}"
    )

    # 3. Cluster centroid
    restaurant_coords = [(r.lat, r.lng) for r in restaurants]
    centroid = _centroid(restaurant_coords)

    # 4. Nearest available rider
    riders_result = await db.execute(
        select(User).where(
            User.role == UserRole.rider,
            User.is_available == True,
            User.current_lat.isnot(None),
            User.current_lng.isnot(None),
        )
    )
    available_riders = riders_result.scalars().all()

    nearest_rider = None
    min_rider_dist = float("inf")
    for rider in available_riders:
        d = _haversine_km(rider.current_lat, rider.current_lng,
                          centroid[0], centroid[1])
        if d < min_rider_dist:
            min_rider_dist = d
            nearest_rider = rider

    assigned_rider_name = nearest_rider.name if nearest_rider else "No rider available"

    # 5. Delivery fee
    route_km = 0.0
    if delivery_lat and delivery_lng:
        if can_batch:
            route_km = min_rider_dist + _haversine_km(
                centroid[0], centroid[1], delivery_lat, delivery_lng
            )
        else:
            for r in restaurants:
                route_km += _haversine_km(centroid[0], centroid[1], r.lat, r.lng)
            route_km += _haversine_km(
                centroid[0], centroid[1], delivery_lat, delivery_lng
            )
    else:
        route_km = min_rider_dist + 3.0

    route_km = max(route_km, 1.0)
    unbatched_fee = (settings.BASE_DELIVERY_FEE * len(restaurants)
                     + route_km * settings.FEE_PER_KM)
    batched_fee = (settings.BASE_DELIVERY_FEE + route_km * settings.FEE_PER_KM) * (
        1 - settings.BATCH_DISCOUNT if can_batch else 1
    )
    delivery_fee = round(batched_fee if can_batch else unbatched_fee, 2)
    estimated_savings = max(0, int(unbatched_fee - batched_fee)) if can_batch else 0

    # 6. ETA
    max_prep = max((r.avg_prep_time_minutes for r in restaurants), default=20)
    rider_to_first = _travel_minutes(min_rider_dist)
    last_to_door = _travel_minutes(
        _haversine_km(
            centroid[0], centroid[1],
            delivery_lat or centroid[0],
            delivery_lng or centroid[1],
        )
    )
    stop_buffer = settings.STOP_BUFFER_MINS * max(0, len(restaurants) - 1)
    eta_mins = int(max(max_prep, rider_to_first) + last_to_door + stop_buffer + 5)
    eta_mins = max(eta_mins, 20)

    return {
        "can_batch": can_batch,
        "estimated_savings": estimated_savings,
        "assigned_rider": assigned_rider_name,
        "estimated_eta": f"{eta_mins} mins",
        "delivery_fee": delivery_fee,
        "batched_restaurant_ids": restaurant_ids if can_batch else [],
        "rider": nearest_rider,
    }


def _fallback_result() -> Dict[str, Any]:
    return {
        "can_batch": False,
        "estimated_savings": 0,
        "assigned_rider": "No rider available",
        "estimated_eta": "45 mins",
        "delivery_fee": 48.0,
        "batched_restaurant_ids": [],
        "rider": None,
    }