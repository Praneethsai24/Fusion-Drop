"""User model — shared by customers and riders (role-based)."""
import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, Enum
from backend.database.connection import Base


class UserRole(str, enum.Enum):
    customer = "customer"
    rider    = "rider"


class User(Base):
    __tablename__ = "users"

    id               = Column(Integer, primary_key=True, index=True)
    name             = Column(String(120), nullable=False)
    email            = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password  = Column(String(255), nullable=False)
    phone            = Column(String(20),  nullable=True)
    role             = Column(Enum(UserRole), nullable=False, default=UserRole.customer)
    is_active        = Column(Boolean, default=True, nullable=False)

    # Rider-only fields (null for customers)
    is_available     = Column(Boolean, default=False, nullable=True)
    current_lat      = Column(Float,   nullable=True)
    current_lng      = Column(Float,   nullable=True)
    vehicle_type     = Column(String(30), nullable=True)   # bike / scooter / cycle

    created_at       = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at       = Column(DateTime,
                              default=lambda: datetime.now(timezone.utc),
                              onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<User id={self.id} email={self.email} role={self.role}>"