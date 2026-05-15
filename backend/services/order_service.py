# backend/services/order_service.py
import logging
from typing import List, Tuple

from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.models.order import Order, OrderItem, OrderStatus
from backend.models.restaurant import MenuItem
from backend.models.user import User
from backend.schemas.order import (
    CheckoutRequest,
    OrderItemResponse,
    OptimizationResult,
)
from backend.services.delivery_optimizer import optimize_delivery

logger = logging.getLogger(__name__)


class OrderService:
    """
    Encapsulates business logic related to orders.

    This keeps FastAPI route handlers focused on HTTP concerns
    (request/response, security, background tasks).
    """

    def __init__(self, db: Session):
        self.db = db

    def _validate_items(self, payload: CheckoutRequest) -> dict[int, MenuItem]:
        item_ids = [ci.menu_item_id for ci in payload.items]
        db_items: dict[int, MenuItem] = {
            mi.id: mi
            for mi in self.db.query(MenuItem)
            .filter(MenuItem.id.in_(item_ids))
            .all()
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
        return db_items

    def _compute_totals(
        self, payload: CheckoutRequest, db_items: dict[int, MenuItem]
    ) -> int:
        return sum(
            db_items[ci.menu_item_id].price * ci.quantity
            for ci in payload.items
        )

    def create_order(
        self,
        payload: CheckoutRequest,
        current_user: User,
    ) -> Tuple[Order, OptimizationResult, List[OrderItemResponse]]:
        """
        Full checkout flow:

        1. Validate cart items.
        2. Run delivery optimisation.
        3. Persist Order + OrderItems.
        4. Mark rider as unavailable.
        """
        # 1. Validate items
        db_items = self._validate_items(payload)

        # 2. Optimise delivery
        item_ids = [ci.menu_item_id for ci in payload.items]
        result = optimize_delivery(
            self.db,
            item_ids,
            payload.delivery_lat,
            payload.delivery_lng,
        )

        # 3. Compute totals
        total_amount = self._compute_totals(payload, db_items)
        eta_int = int(result["estimated_eta"].replace(" mins", "").strip())

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
        self.db.add(order)
        self.db.flush()  # ensure order.id is populated

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
            self.db.add(oi)
            items_out.append(
                OrderItemResponse(
                    id=0,  # will be set after flush if you choose to refresh
                    menu_item_id=ci.menu_item_id,
                    quantity=ci.quantity,
                    unit_price=mi.price,
                    subtotal=mi.price * ci.quantity,
                    item_name=mi.name,
                )
            )

        # Mark rider busy
        if result["rider"]:
            result["rider"].is_available = False

        self.db.commit()
        self.db.refresh(order)

        opt = OptimizationResult(
            can_batch=result["can_batch"],
            estimated_savings=result["estimated_savings"],
            assigned_rider=result["assigned_rider"],
            estimated_eta=result["estimated_eta"],
            batched_restaurant_ids=result["batched_restaurant_ids"],
        )

        logger.info(
            "Order #%s created | customer=%s | batched=%s | rider=%s",
            order.id,
            current_user.id,
            result["can_batch"],
            result["assigned_rider"],
        )
        return order, opt, items_out