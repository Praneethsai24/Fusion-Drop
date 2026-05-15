"""Restaurant and menu-item management."""
import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database.connection import get_db
from backend.models.restaurant import Restaurant, MenuItem
from backend.schemas.restaurant import (
    RestaurantCreate, RestaurantResponse,
    MenuItemCreate, MenuItemResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/restaurants", tags=["Restaurants"])


@router.post("/", response_model=RestaurantResponse, status_code=201)
def create_restaurant(payload: RestaurantCreate, db: Session = Depends(get_db)):
    """Create a new restaurant (admin / seed use)."""
    r = Restaurant(**payload.model_dump())
    db.add(r)
    db.commit()
    db.refresh(r)
    logger.info(f"Restaurant created: {r.name}")
    return r


@router.get("/", response_model=List[RestaurantResponse])
def list_restaurants(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """List all open restaurants with their full menus."""
    return (
        db.query(Restaurant)
        .filter(Restaurant.is_open == True)
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.get("/{restaurant_id}", response_model=RestaurantResponse)
def get_restaurant(restaurant_id: int, db: Session = Depends(get_db)):
    """Fetch one restaurant with its menu."""
    r = db.query(Restaurant).filter(Restaurant.id == restaurant_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    return r


@router.post("/{restaurant_id}/menu", response_model=MenuItemResponse, status_code=201)
def add_menu_item(
    restaurant_id: int,
    payload: MenuItemCreate,
    db: Session = Depends(get_db),
):
    """Add a menu item to a restaurant."""
    if not db.query(Restaurant).filter(Restaurant.id == restaurant_id).first():
        raise HTTPException(status_code=404, detail="Restaurant not found")
    item = MenuItem(restaurant_id=restaurant_id, **payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/menu/{item_id}/availability")
def toggle_menu_item(
    item_id: int,
    available: bool,
    db: Session = Depends(get_db),
):
    """Toggle a menu item's availability (e.g. sold out)."""
    item = db.query(MenuItem).filter(MenuItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Menu item not found")
    item.is_available = available
    db.commit()
    return {"id": item_id, "is_available": available}