"""Pydantic schemas for restaurants and menu items."""
from typing import Optional, List
from pydantic import BaseModel, Field


class MenuItemCreate(BaseModel):
    name:         str   = Field(..., min_length=1, max_length=120)
    description:  Optional[str]  = None
    price:        float = Field(..., gt=0)
    category:     Optional[str]  = None
    is_available: bool  = True


class MenuItemResponse(BaseModel):
    id:           int
    restaurant_id: int
    name:         str
    description:  Optional[str]
    price:        float
    category:     Optional[str]
    is_available: bool

    model_config = {"from_attributes": True}


class RestaurantCreate(BaseModel):
    name:                   str   = Field(..., min_length=2)
    cuisine_type:           Optional[str] = None
    description:            Optional[str] = None
    address:                str
    lat:                    float
    lng:                    float
    avg_prep_time_minutes:  int   = 20
    rating:                 float = 4.0


class RestaurantResponse(BaseModel):
    id:                    int
    name:                  str
    cuisine_type:          Optional[str]
    description:           Optional[str]
    address:               str
    lat:                   float
    lng:                   float
    avg_prep_time_minutes: int
    rating:                float
    is_open:               bool
    image_url:             Optional[str]
    menu_items:            List[MenuItemResponse] = []

    model_config = {"from_attributes": True}