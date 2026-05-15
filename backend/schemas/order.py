"""Pydantic schemas for orders and checkout."""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class CartItem(BaseModel):
    menu_item_id: int
    quantity:     int = Field(..., ge=1, le=50)


class CheckoutRequest(BaseModel):
    items:            List[CartItem] = Field(..., min_length=1)
    delivery_address: str            = Field(..., min_length=5)
    delivery_lat:     Optional[float] = None
    delivery_lng:     Optional[float] = None
    notes:            Optional[str]   = None


class StatusUpdateRequest(BaseModel):
    status:     str
    rider_lat:  Optional[float] = None
    rider_lng:  Optional[float] = None


class OptimizationResult(BaseModel):
    can_batch:              bool
    estimated_savings:      int
    assigned_rider:         str
    estimated_eta:          str
    batched_restaurant_ids: List[int] = []


class OrderItemResponse(BaseModel):
    id:           int
    menu_item_id: int
    quantity:     int
    unit_price:   float
    subtotal:     float
    item_name:    Optional[str] = None

    model_config = {"from_attributes": True}


class OrderResponse(BaseModel):
    id:                    int
    customer_id:           int
    rider_id:              Optional[int]
    status:                str
    total_amount:          float
    delivery_fee:          float
    delivery_address:      str
    estimated_eta_minutes: int
    is_batched:            str
    notes:                 Optional[str]
    items:                 List[OrderItemResponse] = []
    created_at:            Optional[datetime]
    optimization:          Optional[OptimizationResult] = None

    model_config = {"from_attributes": True}