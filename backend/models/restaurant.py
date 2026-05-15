"""Restaurant and MenuItem models."""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from backend.database.connection import Base


class Restaurant(Base):
    __tablename__ = "restaurants"

    id                      = Column(Integer, primary_key=True, index=True)
    name                    = Column(String(120), nullable=False)
    cuisine_type            = Column(String(60),  nullable=True)
    description             = Column(Text,        nullable=True)
    address                 = Column(String(255), nullable=False)
    lat                     = Column(Float,        nullable=False)
    lng                     = Column(Float,        nullable=False)
    avg_prep_time_minutes   = Column(Integer,     default=20)
    rating                  = Column(Float,       default=4.0)
    is_open                 = Column(Boolean,     default=True)
    image_url               = Column(String(500), nullable=True)

    created_at  = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    menu_items = relationship("MenuItem", back_populates="restaurant",
                              cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Restaurant id={self.id} name={self.name}>"


class MenuItem(Base):
    __tablename__ = "menu_items"

    id            = Column(Integer, primary_key=True, index=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=False, index=True)
    name          = Column(String(120), nullable=False)
    description   = Column(Text,        nullable=True)
    price         = Column(Float,       nullable=False)
    category      = Column(String(60),  nullable=True)
    is_available  = Column(Boolean,     default=True)
    image_url     = Column(String(500), nullable=True)

    restaurant = relationship("Restaurant", back_populates="menu_items")

    def __repr__(self):
        return f"<MenuItem id={self.id} name={self.name} price={self.price}>"