"""
Order management — multi-restaurant checkout, status updates,
delivery simulation, and order history.
"""
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from backend.database.connection import get_db
from backend.models.order import Order, OrderItem, OrderStatus
from backend.models.restaurant import MenuItem
from backend.schemas.order import (
    CheckoutRequest, OrderResponse,
    OrderItemResponse, OptimizationResult,
    StatusUpdateRequest,
)
from backend.auth.jwt_handler import get_current_user
from backend.services.delivery_optimizer import optimize_delivery
from backend.websocket.manager import ws_manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/orders", tags=["Orders"])


# ── Checkout ──────────────────────────────────────────────────────

@router.post("/checkout", response_model=OrderResponse, status_code=201)
async def checkout(
    payload: CheckoutRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Multi-restaurant checkout with intelligent delivery batching.

    Flow:
      1. Validate all cart items exist and are available.
      2. Run delivery optimisation (batch check, rider assignment, fee & ETA).
      3. Persist Order + OrderItems.
      4. Mark rider as unavailable.
      5. Launch background delivery simulation.
      6. Return enriched OrderResponse with OptimizationResult.
    """
    # ── 1. Validate items ──────────────────────────────────────────
    item_ids = [ci.menu_item_id for ci in payload.items]
    db_items: dict[int, MenuItem] = {
        mi.id: mi
        for mi in db.query(MenuItem).filter(MenuItem.id.in_(item_ids)).all()
    }
    for ci in payload.items:
        if ci.menu_item_id not in db_items:
            raise HTTPException(
                status_code=404,
                detail=f"Menu item {ci.menu_item_id} not found",
            )
        if not db_items[ci.menu_item_id].is_available:
            raise HTTPException(
                status_code=400,
                detail=f"'{db_items[ci.menu_item_id].name}' is currently unavailable",
            )

    # ── 2. Optimise delivery ───────────────────────────────────────
    result = optimize_delivery(
        db, item_ids,
        payload.delivery_lat,
        payload.delivery_lng,
    )

    # ── 3. Compute totals ──────────────────────────────────────────
    total_amount = sum(
        db_items[ci.menu_item_id].price * ci.quantity
        for ci in payload.items
    )
    eta_int = int(result["estimated_eta"].replace(" mins", "").strip())

    # ── 4. Persist order ───────────────────────────────────────────
    order = Order(
        customer_id=current_user.id,
        rider_id=result["rider"].id if result["rider"] else None,
        status=(
            OrderStatus.rider_assigned
            if result["rider"]
            else OrderStatus.order_received
        ),
        total_amount=total_amount,
        delivery_fee=result["delivery_fee"],
        delivery_address=payload.delivery_address,
        delivery_lat=payload.delivery_lat,
        delivery_lng=payload.delivery_lng,
        is_batched=str(result["can_batch"]).lower(),
        estimated_eta_minutes=eta_int,
        notes=payload.notes,
    )
    db.add(order)
    db.flush()  # get order.id before committing

    items_out: List[OrderItemResponse] = []
    for ci in payload.items:
        mi = db_items[ci.menu_item_id]
        oi = OrderItem(
            order_id=order.id,
            menu_item_id=ci.menu_item_id,
            quantity=ci.quantity,
            unit_price=mi.price,
            subtotal=mi.price * ci.quantity,
        )
        db.add(oi)
        items_out.append(OrderItemResponse(
            id=0,  # will be set after flush
            menu_item_id=ci.menu_item_id,
            quantity=ci.quantity,
            unit_price=mi.price,
            subtotal=mi.price * ci.quantity,
            item_name=mi.name,
        ))

    # Mark rider busy
    if result["rider"]:
        result["rider"].is_available = False

    db.commit()
    db.refresh(order)

    # ── 5. Background delivery simulation ─────────────────────────
    background_tasks.add_task(_simulate_delivery, order.id)
    logger.info(
        f"Order #{order.id} created | customer={current_user.id} "
        f"| batched={result['can_batch']} | rider={result['assigned_rider']}"
    )

    # ── 6. Build response ──────────────────────────────────────────
    opt = OptimizationResult(
        can_batch=result["can_batch"],
        estimated_savings=result["estimated_savings"],
        assigned_rider=result["assigned_rider"],
        estimated_eta=result["estimated_eta"],
        batched_restaurant_ids=result["batched_restaurant_ids"],
    )
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
        raise HTTPException(status_code=400, detail=f"Invalid status. Choose from: {valid}")

    order.status = payload.status

    if payload.rider_lat and payload.rider_lng and order.rider_id:
        from backend.models.user import User
        rider = db.query(User).filter(User.id == order.rider_id).first()
        if rider:
            rider.current_lat = payload.rider_lat
            rider.current_lng = payload.rider_lng

    if payload.status == OrderStatus.delivered and order.rider_id:
        from backend.models.user import User
        rider = db.query(User).filter(User.id == order.rider_id).first()
        if rider:
            rider.is_available = True

    db.commit()

    await ws_manager.broadcast_order_update(order_id, {
        "order_id": order_id,
        "status": payload.status,
        "rider_lat": payload.rider_lat,
        "rider_lng": payload.rider_lng,
        "eta_minutes": order.estimated_eta_minutes,
    })

    return {"order_id": order_id, "status": payload.status}


# ── Background delivery simulation ───────────────────────────────

async def _simulate_delivery(order_id: int) -> None:
    """
    Simulates the full delivery lifecycle by advancing the order through
    each status with realistic delays. Broadcasts every transition via
    the WebSocket manager so the frontend updates in real time.
    """
    import asyncio
    from backend.database.connection import SessionLocal
    from backend.models.order import Order, OrderStatus
    from backend.models.user import User

    # (status, delay_seconds_before_transition)
    STEPS = [
        (OrderStatus.rider_assigned,         4),
        (OrderStatus.picked_from_restaurant, 8),
        (OrderStatus.all_items_picked,       6),
        (OrderStatus.out_for_delivery,       10),
        (OrderStatus.delivered,              12),
    ]

    await asyncio.sleep(3)  # brief initial pause

    db = SessionLocal()
    try:
        for new_status, delay in STEPS:
            await asyncio.sleep(delay)
            order = db.query(Order).filter(Order.id == order_id).first()
            if not order or order.status == OrderStatus.cancelled:
                logger.info(f"[Sim] Order {order_id} cancelled — stopping simulation")
                break

            order.status = new_status

            if new_status == OrderStatus.delivered and order.rider_id:
                rider = db.query(User).filter(User.id == order.rider_id).first()
                if rider:
                    rider.is_available = True

            db.commit()

            await ws_manager.broadcast_order_update(order_id, {
                "order_id": order_id,
                "status": new_status.value,
                "simulated": True,
            })
            logger.info(f"[Sim] Order {order_id} → {new_status.value}")

    except Exception as exc:
        logger.error(f"[Sim] Error for order {order_id}: {exc}")
    finally:
        db.close()