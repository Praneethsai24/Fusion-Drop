"""
Order management — multi-restaurant checkout, status updates,
delivery simulation, cancellation, and order history.
All DB access uses AsyncSession.
"""
import asyncio
import logging
from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.jwt_handler import get_current_user
from backend.database.connection import AsyncSessionLocal, get_db
from backend.models.order import Order, OrderStatus
from backend.models.user import User, UserRole
from backend.schemas.order import (
    CheckoutRequest,
    OrderItemResponse,
    OrderResponse,
    OptimizationResult,
    StatusUpdateRequest,
)
from backend.services.order_service import OrderService
from backend.websocket.manager import ws_manager
from backend.core.exceptions import NotFoundError, UnauthorizedError, BadRequestError
from backend.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/orders", tags=["Orders"])


# ── Dependency ────────────────────────────────────────────────────────────────

async def get_order_service(
    db: AsyncSession = Depends(get_db),
) -> OrderService:
    """Yield a fully-wired OrderService bound to the current request session."""
    return OrderService(db=db)


# ── Checkout ──────────────────────────────────────────────────────────────────

@router.post("/checkout", response_model=OrderResponse, status_code=201)
async def checkout(
    payload: CheckoutRequest,
    background_tasks: BackgroundTasks,
    order_service: OrderService = Depends(get_order_service),
    current_user: User = Depends(get_current_user),
):
    """
    Multi-restaurant checkout with intelligent delivery batching.

    Heavy business logic is handled by OrderService. The handler is
    responsible only for HTTP concerns and scheduling the background simulation.
    """
    order, opt, items_out = await order_service.create_order(payload, current_user)

    # Fire-and-forget delivery simulation (does not block the response)
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


# ── Order history ─────────────────────────────────────────────────────────────

@router.get("/my", response_model=List[OrderResponse])
async def my_orders(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
):
    """
    Return all orders placed by the authenticated customer,
    newest first. Supports pagination via skip/limit.
    """
    result = await db.execute(
        select(Order)
        .where(Order.customer_id == current_user.id)
        .order_by(Order.id.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Fetch a single order.
    Only the order's customer or its assigned rider may access it.
    """
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()

    if not order:
        raise NotFoundError("Order", order_id)
    if order.customer_id != current_user.id and order.rider_id != current_user.id:
        raise UnauthorizedError("Access denied — this order does not belong to you.")

    return order


# ── Status update (rider / admin action) ─────────────────────────────────────

@router.patch("/{order_id}/status")
async def update_order_status(
    order_id: int,
    payload: StatusUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update order status and broadcast the change via WebSocket.
    Accepts optional rider GPS coordinates for live tracking.
    """
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise NotFoundError("Order", order_id)

    valid_statuses = [s.value for s in OrderStatus]
    if payload.status not in valid_statuses:
        raise BadRequestError(
            f"Invalid status '{payload.status}'. Valid values: {valid_statuses}"
        )

    # Prevent invalid state transitions
    _validate_status_transition(order.status, payload.status)

    order.status = payload.status

    # Update rider GPS if provided
    if payload.rider_lat and payload.rider_lng and order.rider_id:
        rider_result = await db.execute(
            select(User).where(User.id == order.rider_id)
        )
        rider = rider_result.scalar_one_or_none()
        if rider:
            rider.current_lat = payload.rider_lat
            rider.current_lng = payload.rider_lng

    # Free the rider when delivery is complete
    if payload.status == OrderStatus.delivered and order.rider_id:
        rider_result = await db.execute(
            select(User).where(User.id == order.rider_id)
        )
        rider = rider_result.scalar_one_or_none()
        if rider:
            rider.is_available = True

    await db.commit()

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

    logger.info("order_status_updated", order_id=order_id, status=payload.status,
                updated_by=current_user.id)
    return {"order_id": order_id, "status": payload.status}


# ── Cancellation ──────────────────────────────────────────────────────────────

@router.post("/{order_id}/cancel")
async def cancel_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Cancel an order. Only the placing customer may cancel,
    and only before a rider has been assigned.
    """
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()

    if not order:
        raise NotFoundError("Order", order_id)
    if order.customer_id != current_user.id:
        raise UnauthorizedError("Only the order's customer can cancel it.")

    # Business rule: cannot cancel once a rider is en-route
    non_cancellable = {
        OrderStatus.picked_from_restaurant,
        OrderStatus.all_items_picked,
        OrderStatus.out_for_delivery,
        OrderStatus.delivered,
    }
    if order.status in non_cancellable:
        raise BadRequestError(
            f"Cannot cancel an order with status '{order.status.value}'. "
            "The rider is already on the way."
        )
    if order.status == OrderStatus.cancelled:
        raise BadRequestError("Order is already cancelled.")

    # Free the rider if one was assigned
    if order.rider_id:
        rider_result = await db.execute(
            select(User).where(User.id == order.rider_id)
        )
        rider = rider_result.scalar_one_or_none()
        if rider:
            rider.is_available = True
        order.rider_id = None

    order.status = OrderStatus.cancelled
    await db.commit()

    await ws_manager.broadcast_order_update(
        order_id,
        {"order_id": order_id, "status": OrderStatus.cancelled.value},
    )

    logger.info("order_cancelled", order_id=order_id, customer_id=current_user.id)
    return {"order_id": order_id, "status": OrderStatus.cancelled.value}


# ── State machine guard ───────────────────────────────────────────────────────

_VALID_TRANSITIONS: dict[str, set[str]] = {
    OrderStatus.order_received.value: {
        OrderStatus.rider_assigned.value,
        OrderStatus.cancelled.value,
    },
    OrderStatus.rider_assigned.value: {
        OrderStatus.picked_from_restaurant.value,
        OrderStatus.cancelled.value,
    },
    OrderStatus.picked_from_restaurant.value: {
        OrderStatus.all_items_picked.value,
    },
    OrderStatus.all_items_picked.value: {
        OrderStatus.out_for_delivery.value,
    },
    OrderStatus.out_for_delivery.value: {
        OrderStatus.delivered.value,
    },
    OrderStatus.delivered.value: set(),
    OrderStatus.cancelled.value: set(),
}


def _validate_status_transition(current: OrderStatus, next_status: str) -> None:
    allowed = _VALID_TRANSITIONS.get(current.value, set())
    if next_status not in allowed:
        raise BadRequestError(
            f"Cannot transition from '{current.value}' to '{next_status}'. "
            f"Allowed next statuses: {sorted(allowed) or ['none (terminal state)']}"
        )


# ── Background delivery simulation ───────────────────────────────────────────

async def _simulate_delivery(order_id: int) -> None:
    """
    Simulates the full delivery lifecycle by advancing the order through
    each status with realistic delays. Uses its own AsyncSession so it
    is fully decoupled from the request session that has already responded.
    """
    STEPS = [
        (OrderStatus.rider_assigned, 4),
        (OrderStatus.picked_from_restaurant, 8),
        (OrderStatus.all_items_picked, 6),
        (OrderStatus.out_for_delivery, 10),
        (OrderStatus.delivered, 12),
    ]

    await asyncio.sleep(3)  # brief pause before the first transition

    async with AsyncSessionLocal() as db:
        try:
            for new_status, delay in STEPS:
                await asyncio.sleep(delay)

                result = await db.execute(select(Order).where(Order.id == order_id))
                order = result.scalar_one_or_none()

                if not order:
                    logger.warning("sim_order_missing", order_id=order_id)
                    return
                if order.status == OrderStatus.cancelled:
                    logger.info("sim_stopped_cancelled", order_id=order_id)
                    return

                order.status = new_status

                if new_status == OrderStatus.delivered and order.rider_id:
                    rider_result = await db.execute(
                        select(User).where(User.id == order.rider_id)
                    )
                    rider = rider_result.scalar_one_or_none()
                    if rider:
                        rider.is_available = True

                await db.commit()

                await ws_manager.broadcast_order_update(
                    order_id,
                    {
                        "order_id": order_id,
                        "status": new_status.value,
                        "simulated": True,
                    },
                )
                logger.info("sim_step", order_id=order_id, status=new_status.value)

        except Exception as exc:
            await db.rollback()
            logger.error("sim_error", order_id=order_id, error=str(exc))