"""
Order service — fully async checkout business logic.

FIX: Replaced synchronous sqlalchemy.orm.Session with AsyncSession.
     Replaced self.db.query(...) with await db.execute(select(...)).
     Confirmed optimize_delivery() is properly awaited.
     (Blocker #3 — MissingGreenlet / sync Session in async context)
"""
import logging
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.core.exceptions import NotFoundError, BadRequestError
from backend.models.order import Order, OrderItem, OrderStatus
from backend.models.restaurant import MenuItem
from backend.models.user import User
from backend.schemas.order import CheckoutRequest
from backend.services.delivery_optimizer import optimize_delivery

logger = logging.getLogger(__name__)


class OrderService:
    """
    Encapsulates business logic for order creation.
    All methods are async and use AsyncSession exclusively.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _validate_items(
        self, payload: CheckoutRequest
    ) -> dict[int, MenuItem]:
        """Load and validate menu items. Returns {menu_item_id: MenuItem} map."""
        item_ids = [ci.menu_item_id for ci in payload.items]
        result = await self.db.execute(
            select(MenuItem).where(MenuItem.id.in_(item_ids))
        )
        db_items: dict[int, MenuItem] = {
            mi.id: mi for mi in result.scalars().all()
        }
        for ci in payload.items:
            if ci.menu_item_id not in db_items:
                raise NotFoundError("MenuItem", ci.menu_item_id)
            if not db_items[ci.menu_item_id].is_available:
                raise BadRequestError(
                    f"'{db_items[ci.menu_item_id].name}' is currently unavailable"
                )
        return db_items

    def _compute_total(
        self,
        payload: CheckoutRequest,
        db_items: dict[int, MenuItem],
    ) -> float:
        return sum(
            db_items[ci.menu_item_id].price * ci.quantity
            for ci in payload.items
        )

    async def create_order(
        self,
        payload: CheckoutRequest,
        current_user: User,
    ) -> Order:
        """
        Full checkout flow:
          1. Validate cart items against DB
          2. Run async delivery optimisation (haversine batching)
          3. Persist Order + OrderItems in a single transaction
          4. Mark assigned rider as unavailable
        """
        db_items = await self._validate_items(payload)

        item_ids = [ci.menu_item_id for ci in payload.items]
        opt_result = await optimize_delivery(   # properly awaited
            self.db,
            item_ids,
            payload.delivery_lat,
            payload.delivery_lng,
        )

        total_amount = self._compute_total(payload, db_items)

        order = Order(
            customer_id=current_user.id,
            rider_id=opt_result["rider"].id if opt_result.get("rider") else None,
            status=(
                OrderStatus.rider_assigned
                if opt_result.get("rider")
                else OrderStatus.order_received
            ),
            total_amount=total_amount,
            delivery_fee=opt_result.get("delivery_fee", 30.0),
            delivery_address=payload.delivery_address,
            delivery_lat=payload.delivery_lat,
            delivery_lng=payload.delivery_lng,
            is_batched=opt_result.get("can_batch", False),  # Boolean now
            estimated_eta_minutes=int(opt_result.get("estimated_eta_minutes", 45)),
            notes=payload.notes,
        )
        self.db.add(order)
        await self.db.flush()  # get order.id

        for ci in payload.items:
            self.db.add(OrderItem(
                order_id=order.id,
                menu_item_id=ci.menu_item_id,
                quantity=ci.quantity,
                unit_price=db_items[ci.menu_item_id].price,
                restaurant_id=db_items[ci.menu_item_id].restaurant_id,
            ))

        if opt_result.get("rider"):
            opt_result["rider"].is_available = False

        await self.db.commit()
        await self.db.refresh(order)
        logger.info("order_created", order_id=order.id, customer_id=current_user.id)
        return order