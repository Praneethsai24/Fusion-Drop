"""
Delivery Optimizer Service
===========================
Core business logic for FusionDrop's intelligent delivery batching.

Algorithm:
  1. Collect all unique restaurants in the cart.
  2. Compute pairwise Haversine distances between restaurants.
  3. If ALL pairs are <= BATCH_RADIUS_KM → can_batch = True.
  4. Find the nearest available rider to the restaurant cluster centroid.
  5. Estimate delivery fee (base + km-rate, discounted when batched).
  6. Estimate ETA (prep time + rider travel + stop buffers).

Returns a dict that drives the checkout endpoint.
"""
import math
import logging
from typing import List, Optional, Dict, Any

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# ── Tunable constants ─────────────────────────────────────────────
BATCH_RADIUS_KM  = 3.0    # restaurants within this distance can be batched
BASE_FEE         = 30.0   # ₹ flat base delivery fee
FEE_PER_KM       = 8.0    # ₹ per km
BATCH_DISCOUNT   = 0.25   # 25% discount when batching
AVG_RIDER_SPEED  = 25.0   # km/h (city average)
STOP_BUFFER_MINS = 3      # extra minutes per additional restaurant stop


# ── Haversine distance ────────────────────────────────────────────

def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance between two GPS coordinates in kilometres."""
    R = 6371.0
    φ1, φ2 = math.radians(lat1), math.radians(lat2)
    Δφ     = math.radians(lat2 - lat1)
    Δλ     = math.radians(lng2 - lng1)
    a = math.sin(Δφ / 2) ** 2 + math.cos(φ1) * math.cos(φ2) * math.sin(Δλ / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _centroid(coords: List[tuple]) -> tuple:
    """Arithmetic mean of a list of (lat, lng) tuples."""
    if not coords:
        return (12.9716, 77.5946)  # Bengaluru city centre fallback
    return (
        sum(c[0] for c in coords) / len(coords),
        sum(c[1] for c in coords) / len(coords),
    )


def _travel_minutes(distance_km: float) -> float:
    return (distance_km / AVG_RIDER_SPEED) * 60


# ── Main optimisation function ────────────────────────────────────

def optimize_delivery(
    db: Session,
    menu_item_ids: List[int],
    delivery_lat: Optional[float],
    delivery_lng: Optional[float],
) -> Dict[str, Any]:
    """
    Run delivery optimisation for a multi-restaurant cart.

    Parameters
    ----------
    db            : SQLAlchemy session
    menu_item_ids : IDs of all menu items in the cart
    delivery_lat  : Customer delivery latitude
    delivery_lng  : Customer delivery longitude

    Returns
    -------
    {
        "can_batch":              bool,
        "estimated_savings":      int,       # ₹ saved vs separate deliveries
        "assigned_rider":         str,        # rider name or "No rider available"
        "estimated_eta":          str,        # e.g. "38 mins"
        "delivery_fee":           float,
        "batched_restaurant_ids": list[int],
        "rider":                  User | None,
    }
    """
    from backend.models.restaurant import MenuItem, Restaurant
    from backend.models.user import User, UserRole

    # 1. Gather unique restaurants
    items = db.query(MenuItem).filter(MenuItem.id.in_(menu_item_ids)).all()
    restaurant_ids = list({i.restaurant_id for i in items})
    restaurants = db.query(Restaurant).filter(Restaurant.id.in_(restaurant_ids)).all()

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
            if d > BATCH_RADIUS_KM:
                can_batch = False

    logger.info(
        f"Delivery optimisation: {len(restaurants)} restaurant(s), "
        f"max inter-restaurant distance {max_inter_restaurant_km:.2f} km, "
        f"can_batch={can_batch}"
    )

    # 3. Cluster centroid (for finding nearest rider)
    restaurant_coords = [(r.lat, r.lng) for r in restaurants]
    centroid = _centroid(restaurant_coords)

    # 4. Nearest available rider
    available_riders = db.query(User).filter(
        User.role == UserRole.rider,
        User.is_available == True,
        User.current_lat.isnot(None),
        User.current_lng.isnot(None),
    ).all()

    nearest_rider = None
    min_rider_dist = float("inf")
    for rider in available_riders:
        d = _haversine_km(rider.current_lat, rider.current_lng, centroid[0], centroid[1])
        if d < min_rider_dist:
            min_rider_dist = d
            nearest_rider = rider

    assigned_rider_name = nearest_rider.name if nearest_rider else "No rider available"

    # 5. Delivery fee
    route_km = 0.0
    if delivery_lat and delivery_lng:
        if can_batch:
            # Rider → centroid → delivery point
            route_km = min_rider_dist + _haversine_km(
                centroid[0], centroid[1], delivery_lat, delivery_lng
            )
        else:
            # Sum of: rider→each restaurant→delivery (worst-case separate)
            for r in restaurants:
                route_km += _haversine_km(centroid[0], centroid[1], r.lat, r.lng)
            route_km += _haversine_km(centroid[0], centroid[1], delivery_lat, delivery_lng)
    else:
        route_km = min_rider_dist + 3.0  # rough fallback

    route_km = max(route_km, 1.0)
    unbatched_fee = BASE_FEE * len(restaurants) + route_km * FEE_PER_KM
    batched_fee   = (BASE_FEE + route_km * FEE_PER_KM) * (1 - BATCH_DISCOUNT if can_batch else 1)
    delivery_fee  = round(batched_fee if can_batch else unbatched_fee, 2)
    estimated_savings = max(0, int(unbatched_fee - batched_fee)) if can_batch else 0

    # 6. ETA
    max_prep = max((r.avg_prep_time_minutes for r in restaurants), default=20)
    rider_to_first = _travel_minutes(min_rider_dist)
    last_to_door   = _travel_minutes(
        _haversine_km(centroid[0], centroid[1], delivery_lat or centroid[0], delivery_lng or centroid[1])
    )
    stop_buffer = STOP_BUFFER_MINS * max(0, len(restaurants) - 1)
    eta_mins    = int(max(max_prep, rider_to_first) + last_to_door + stop_buffer + 5)
    eta_mins    = max(eta_mins, 20)  # floor

    return {
        "can_batch":              can_batch,
        "estimated_savings":      estimated_savings,
        "assigned_rider":         assigned_rider_name,
        "estimated_eta":          f"{eta_mins} mins",
        "delivery_fee":           delivery_fee,
        "batched_restaurant_ids": restaurant_ids if can_batch else [],
        "rider":                  nearest_rider,
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