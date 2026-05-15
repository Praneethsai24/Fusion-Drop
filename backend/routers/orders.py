# backend/routers/orders.py
"""
Order management — multi-restaurant checkout, status updates,
delivery simulation, and order history.
"""
import logging
from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.auth.jwt_handler import get_current_user
from backend.database.connection import SessionLocal, get_db
from backend.models.order import Order, OrderStatus
from backend.models.user import User
from backend.schemas.order import (
    CheckoutRequest,
    OrderItemResponse,
    OrderResponse,
    OptimizationResult,
    StatusUpdateRequest,
)
from backend.services.order_service import OrderService
from backend.websocket.manager import ws_manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/orders", tags=["Orders"])


def get_order_service(db: Session = Depends(get_db)) -> OrderService:
    """
    Dependency-injected OrderService.

    This is a standard FastAPI DI pattern: routes depend on `OrderService`,
    which itself depends on a database session.[cite:3][cite:1]
    """
    return OrderService(db=db)


# ── Checkout ──────────────────────────────────────────────────────


@router.post("/checkout", response_model=OrderResponse, status_code=201)
async def checkout(
    payload: CheckoutRequest,
    background_tasks: BackgroundTasks,
    order_service: OrderService = Depends(get_order_service),
    current_user: User = Depends(get_current_user),
):
    """
    Multi-restaurant checkout with intelligent delivery batching.

    The heavy business logic is delegated to OrderService to keep the
    handler focused on HTTP concerns and background task scheduling.
    """
    order, opt, items_out = order_service.create_order(payload, current_user)

    # Background delivery simulation (unchanged)
    background_tasks.add_task(_simulate_delivery, order.id)

    return OrderResponse(
        id=order.id,
        customer_id=order.customer_id,
        rider_id=order.rider_id,
        status=order.status,
        total_amount=order.total_amount,
        delivery_fee=order.delivery_fee,
        delivery_address=order.delivery_address,
        estimated_eta_minutes=order.estimated_eta_minutes,
        is_batched=order.is_batched,
        notes=order.notes,
        items=items_out,
        created_at=order.created_at,
        optimization=opt,
    )


# ── Order history ─────────────────────────────────────────────────


@router.get("/my", response_model=List[OrderResponse])
def my_orders(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Return all orders placed by the authenticated customer."""
    return (
        db.query(Order)
        .filter(Order.customer_id == current_user.id)
        .order_by(Order.id.desc())
        .all()
    )


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Fetch a single order (must belong to the current user or their rider)."""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.customer_id != current_user.id and order.rider_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return order


# ── Status update (rider action) ──────────────────────────────────


@router.patch("/{order_id}/status")
async def update_order_status(
    order_id: int,
    payload: StatusUpdateRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Update order status and broadcast via WebSocket.
    Accepts optional rider GPS coordinates for live tracking.
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    valid = [s.value for s in OrderStatus]
    if payload.status not in valid:
        raise HTTPException(
            status_code=400, detail=f"Invalid status. Choose from: {valid}"
        )

    order.status = payload.status

    if payload.rider_lat and payload.rider_lng and order.rider_id:
        rider = db.query(User).filter(User.id == order.rider_id).first()
        if rider:
            rider.current_lat = payload.rider_lat
            rider.current_lng = payload.rider_lng

    if payload.status == OrderStatus.delivered and order.rider_id:
        rider = db.query(User).filter(User.id == order.rider_id).first()
        if rider:
            rider.is_available = True

    db.commit()

    await ws_manager.broadcast_order_update(
        order_id,
        {
            "order_id": order_id,
            "status": payload.status,
            "rider_lat": payload.rider_lat,
            "rider_lng": payload.rider_lng,
            "eta_minutes": order.estimated_eta_minutes,
        },
    )

    return {"order_id": order_id, "status": payload.status}


# ── Background delivery simulation ───────────────────────────────


async def _simulate_delivery(order_id: int) -> None:
    """
    Simulates the full delivery lifecycle by advancing the order through
    each status with realistic delays. Broadcasts every transition via
    the WebSocket manager so the frontend updates in real time.
    """
    import asyncio

    from backend.models.order import Order, OrderStatus
    from backend.models.user import User

    # (status, delay_seconds_before_transition)
    STEPS = [
        (OrderStatus.rider_assigned, 4),
        (OrderStatus.picked_from_restaurant, 8),
        (OrderStatus.all_items_picked, 6),
        (OrderStatus.out_for_delivery, 10),
        (OrderStatus.delivered, 12),
    ]

    await asyncio.sleep(3)  # brief initial pause

    db = SessionLocal()
    try:
        for new_status, delay in STEPS:
            await asyncio.sleep(delay)
            order = db.query(Order).filter(Order.id == order_id).first()
            if not order or order.status == OrderStatus.cancelled:
                logger.info("[Sim] Order %s cancelled — stopping simulation", order_id)
                break

            order.status = new_status

            if new_status == OrderStatus.delivered and order.rider_id:
                rider = db.query(User).filter(User.id == order.rider_id).first()
                if rider:
                    rider.is_available = True

            db.commit()

            await ws_manager.broadcast_order_update(
                order_id,
                {
                    "order_id": order_id,
                    "status": new_status.value,
                    "simulated": True,
                },
            )
            logger.info("[Sim] Order %s → %s", order_id, new_status.value)

    except Exception as exc:
        logger.error("[Sim] Error for order %s: %s", order_id, exc)
    finally:
        db.close()