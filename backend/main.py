"""
FusionDrop Backend — FastAPI Application Factory.
Run: uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from backend.core.config import get_settings
from backend.core.logging import setup_logging, get_logger
from backend.core.exceptions import register_exception_handlers
from backend.database.connection import init_db

# Router imports at the top — avoids circular import confusion
from backend.routers import auth, restaurants, orders, riders

setup_logging()
settings = get_settings()
logger = get_logger(__name__)
limiter = Limiter(key_func=get_remote_address)

API_V1 = "/api/v1"


# ── Application lifespan ──────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: initialise DB tables and seed demo data. Shutdown: log."""
    await init_db()
    await _seed_demo_data()
    logger.info(
        "startup_complete",
        version=settings.APP_VERSION,
        env=settings.ENVIRONMENT,
    )
    yield
    logger.info("shutdown", service=settings.APP_NAME)


# ── App factory ───────────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── Rate limiting ─────────────────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Exception handlers ────────────────────────────────────────────────────────
register_exception_handlers(app)

# ── Prometheus metrics ────────────────────────────────────────────────────────
Instrumentator().instrument(app).expose(app, endpoint="/metrics")

# ── Versioned API routers ─────────────────────────────────────────────────────
app.include_router(auth.router,        prefix=API_V1)
app.include_router(restaurants.router, prefix=API_V1)
app.include_router(orders.router,      prefix=API_V1)
app.include_router(riders.router,      prefix=API_V1)


# ── Health check ──────────────────────────────────────────────────────────────

@app.get("/health", tags=["System"])
async def health():
    return {
        "status": "ok",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
    }


# ── Authenticated WebSocket ───────────────────────────────────────────────────

@app.websocket("/ws/orders/{order_id}")
async def order_ws(
    websocket: WebSocket,
    order_id: int,
    token: str = Query(..., description="JWT access token"),
):
    """
    Real-time order tracking WebSocket.
    Requires a valid JWT via ?token=<access_token> query parameter.
    Only the order's customer or assigned rider may connect.
    Close codes: 4001 = Unauthorized, 4003 = Forbidden, 4004 = Not Found.
    """
    from sqlalchemy import select
    from backend.core.security import decode_access_token
    from backend.core.exceptions import UnauthorizedError
    from backend.database.connection import AsyncSessionLocal
    from backend.models.order import Order
    from backend.websocket.manager import ws_manager

    # 1. Authenticate — validate the JWT
    try:
        payload = decode_access_token(token)
        user_id = int(payload["sub"])
    except (UnauthorizedError, ValueError, KeyError):
        await websocket.close(code=4001, reason="Unauthorized: invalid or expired token")
        return

    # 2. Authorize — only the order's customer or rider may subscribe
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Order).where(Order.id == order_id))
        order = result.scalar_one_or_none()

    if not order:
        await websocket.close(code=4004, reason="Order not found")
        return

    if order.customer_id != user_id and order.rider_id != user_id:
        await websocket.close(code=4003, reason="Forbidden: not your order")
        return

    # 3. Accept and register the connection
    await ws_manager.connect(websocket, order_id)
    logger.info("ws_connected", order_id=order_id, user_id=user_id)

    try:
        while True:
            data = await websocket.receive_text()
            if data.strip() == "ping":
                await websocket.send_json({"event": "pong"})
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, order_id)
        logger.info("ws_disconnected", order_id=order_id, user_id=user_id)


# ── Demo data seeder (extracted from lifespan) ────────────────────────────────

async def _seed_demo_data() -> None:
    """
    Seed demo restaurants, menu items, riders, and a customer on a fresh DB.
    Skips silently if data already exists.
    """
    from sqlalchemy import select
    from backend.database.connection import AsyncSessionLocal
    from backend.models.restaurant import Restaurant, MenuItem
    from backend.models.user import User, UserRole
    from backend.core.security import hash_password

    SEED_RESTAURANTS = [
        {
            "name": "Spice Garden",
            "cuisine_type": "Indian",
            "description": "Authentic North Indian curries",
            "address": "MG Road, Bengaluru",
            "lat": 12.9756,
            "lng": 77.6010,
            "avg_prep_time_minutes": 25,
            "rating": 4.5,
            "menu": [
                ("Butter Chicken", "Creamy tomato curry", 320, "Main"),
                ("Garlic Naan", "Soft flatbread", 60, "Bread"),
                ("Dal Makhani", "Black lentils", 220, "Main"),
                ("Mango Lassi", "Sweet yogurt drink", 90, "Drinks"),
            ],
        },
        {
            "name": "Burger Barn",
            "cuisine_type": "American",
            "description": "Gourmet smash burgers",
            "address": "Koramangala, Bengaluru",
            "lat": 12.9352,
            "lng": 77.6245,
            "avg_prep_time_minutes": 15,
            "rating": 4.3,
            "menu": [
                ("Classic Smash Burger", "Double patty, cheddar", 280, "Burgers"),
                ("BBQ Bacon Burger", "Smoky BBQ sauce", 340, "Burgers"),
                ("Loaded Fries", "Cheese sauce, jalapeños", 150, "Sides"),
                ("Chocolate Shake", "Thick shake", 180, "Drinks"),
            ],
        },
        {
            "name": "Sushi Sensei",
            "cuisine_type": "Japanese",
            "description": "Premium nigiri and rolls",
            "address": "Indiranagar, Bengaluru",
            "lat": 12.9784,
            "lng": 77.6408,
            "avg_prep_time_minutes": 30,
            "rating": 4.7,
            "menu": [
                ("Salmon Nigiri (6pc)", "Fresh salmon", 420, "Nigiri"),
                ("Dragon Roll", "Prawn tempura, avocado", 520, "Rolls"),
                ("Miso Soup", "Traditional soybean soup", 120, "Sides"),
                ("Matcha Cheesecake", "Creamy green tea dessert", 260, "Desserts"),
            ],
        },
    ]