"""
Shared pytest fixtures for the FusionDrop test suite.
Provides an async test client, a scoped DB session, and auth helpers.
"""
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from backend.main import app
from backend.database.connection import Base, get_db

TEST_DATABASE_URL = "postgresql+asyncpg://fusiondrop:fusiondrop@localhost:5432/fusiondrop_test"

_engine = create_async_engine(TEST_DATABASE_URL, echo=False, pool_pre_ping=True)
_TestSessionLocal = async_sessionmaker(
    bind=_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


# ── Database lifecycle ────────────────────────────────────────────────────────

@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database():
    """Create all tables before the session, drop them after."""
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await _engine.dispose()


@pytest_asyncio.fixture
async def db_session(setup_database) -> AsyncGenerator[AsyncSession, None]:
    """Yield a per-test async session that is always rolled back on teardown."""
    async with _TestSessionLocal() as session:
        yield session
        await session.rollback()


# ── HTTP client ───────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Yield an AsyncClient backed by the test DB session.
    The real get_db dependency is overridden so every request
    shares the same transactional session as the test.
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


# ── Auth helpers ──────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def customer_headers(client: AsyncClient) -> dict:
    """Register a fresh customer and return their Bearer headers."""
    await client.post("/auth/customer/signup", json={
        "name": "Test Customer",
        "email": "customer_fixture@test.com",
        "password": "testpass123",
        "phone": "9876543210",
    })
    resp = await client.post("/auth/login", json={
        "email": "customer_fixture@test.com",
        "password": "testpass123",
    })
    assert resp.status_code == 200, f"Fixture login failed: {resp.text}"
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def rider_headers(client: AsyncClient) -> dict:
    """Register a fresh rider and return their Bearer headers."""
    await client.post("/auth/rider/signup", json={
        "name": "Test Rider",
        "email": "rider_fixture@test.com",
        "password": "riderpass123",
        "phone": "9123456780",
        "vehicle_type": "bike",
        "current_lat": 12.9716,
        "current_lng": 77.5946,
    })
    resp = await client.post("/auth/login", json={
        "email": "rider_fixture@test.com",
        "password": "riderpass123",
    })
    assert resp.status_code == 200, f"Fixture rider login failed: {resp.text}"
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def seeded_restaurant(client: AsyncClient) -> dict:
    """Create a restaurant with one menu item and return the restaurant dict."""
    resp = await client.post("/restaurants/", json={
        