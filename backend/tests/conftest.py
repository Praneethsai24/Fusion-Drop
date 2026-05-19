"""
Shared pytest fixtures for the FusionDrop test suite.

FIX: Replaced hardcoded PostgreSQL test URL with SQLite in-memory.
     Tests now run on any machine without a local PostgreSQL install.
     (Blocker #7 — tests failed immediately without fusiondrop_test DB)

     To use PostgreSQL instead, set:
       TEST_DATABASE_URL=postgresql+asyncpg://... pytest
"""
import os
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from backend.main import app
from backend.database.connection import Base, get_db

# Default to SQLite in-memory; override via env variable
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "sqlite+aiosqlite:///:memory:",  # FIXED: was postgresql://... hardcoded
)

_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    # SQLite needs connect_args for async compatibility
    connect_args={"check_same_thread": False} if "sqlite" in TEST_DATABASE_URL else {},
)
_TestSessionLocal = async_sessionmaker(
    bind=_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database():
    """Create all tables before the session; drop after."""
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await _engine.dispose()


@pytest_asyncio.fixture
async def db_session(setup_database) -> AsyncGenerator[AsyncSession, None]:
    """Yield a per-test async session, always rolled back on teardown."""
    async with _TestSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Yield an AsyncClient backed by the test DB session.
    Overrides get_db so every request shares the test transaction.
    """
    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def seeded_restaurant(db_session: AsyncSession):
    """Create a test restaurant with menu items and return its data."""
    from backend.models.restaurant import Restaurant, MenuItem

    restaurant = Restaurant(
        name="Test Dhaba",
        cuisine_type="Indian",
        description="Test restaurant",
        address="123 Test Street, Bengaluru",
        lat=12.9716,
        lng=77.5946,
        avg_prep_time_minutes=20,
        rating=4.0,
        is_open=True,
    )
    db_session.add(restaurant)
    await db_session.flush()

    items = [
        MenuItem(restaurant_id=restaurant.id, name="Paneer Butter Masala",
                 description="Rich curry", price=280.0, category="Main", is_available=True),
        MenuItem(restaurant_id=restaurant.id, name="Dal Tadka",
                 description="Yellow lentils", price=180.0, category="Main", is_available=True),
        MenuItem(restaurant_id=restaurant.id, name="Roti",
                 description="Flatbread", price=30.0, category="Bread", is_available=True),
    ]
    for item in items:
        db_session.add(item)
    await db_session.commit()
    await db_session.refresh(restaurant)

    return {"id": restaurant.id, "menu_items": [
        {"id": item.id, "name": item.name, "price": item.price}
        for item in items
    ]}


@pytest_asyncio.fixture
async def customer_headers(client: AsyncClient) -> dict:
    """Register a fresh customer and return Bearer headers."""
    resp = await client.post("/api/v1/auth/customer/signup", json={
        "name": "Test Customer",
        "email": "customer_fixture@test.com",
        "password": "testpass123!",
        "phone": "9876543210",
    })
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def rider_headers(client: AsyncClient) -> dict:
    """Register a fresh rider and return Bearer headers."""
    resp = await client.post("/api/v1/auth/rider/signup", json={
        "name": "Test Rider",
        "email": "rider_fixture@test.com",
        "password": "riderpass123!",
        "phone": "9123456780",
        "vehicle_type": "bike",
        "current_lat": 12.9716,
        "current_lng": 77.5946,
    })
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}