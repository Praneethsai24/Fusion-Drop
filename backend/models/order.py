"""Order and OrderItem models with full delivery state machine."""
import enum
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Float, Boolean,
    DateTime, ForeignKey, Enum, Text
)
from sqlalchemy.orm import relationship
from backend.database.connection import Base


class OrderStatus(str, enum.Enum):
    order_received        = "order_received"
    rider_assigned        = "rider_assigned"
    picked_from_restaurant = "picked_from_restaurant"
    all_items_picked      = "all_items_picked"
    out_for_delivery      = "out_for_delivery"
    delivered             = "delivered"
    cancelled             = "cancelled"


class Order(Base):
    __tablename__ = "orders"

    id                     = Column(Integer, primary_key=True, index=True)
    customer_id            = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    rider_id               = Column(Integer, ForeignKey("users.id"), nullable=True,  index=True)

    status                 = Column(Enum(OrderStatus), default=OrderStatus.order_received, nullable=False)

    total_amount           = Column(Float,   nullable=False)
    delivery_fee           = Column(Float,   default=30.0)
    delivery_address       = Column(String(300), nullable=False)
    delivery_lat           = Column(Float,   nullable=True)
    delivery_lng           = Column(Float,   nullable=True)

    is_batched             = Column(String(10), default="false")   # "true"/"false" string
    estimated_eta_minutes  = Column(Integer,  default=45)
    notes                  = Column(Text,     nullable=True)

    created_at  = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at  = Column(DateTime,
                         default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc))

    items = relationship("OrderItem", back_populates="order",
                         cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Order id={self.id} status={self.status} total={self.total_amount}>"


class OrderItem(Base):
    __tablename__ = "order_items"

    id            = Column(Integer, primary_key=True, index=True)
    order_id      = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    menu_item_id  = Column(Integer, ForeignKey("menu_items.id"), nullable=False)
    quantity      = Column(Integer, nullable=False, default=1)
    unit_price    = Column(Float,   nullable=False)
    subtotal      = Column(Float,   nullable=False)

    order = relationship("Order", back_populates="items")

    def __repr__(self):
        return f"<OrderItem order={self.order_id} item={self.menu_item_id} qty={self.quantity}>"