"""
FusionDrop Backend — FastAPI Application Factory
Run: uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from backend.config import get_settings
from backend.core.logging import setup_logging, get_logger
from backend.core.exceptions import register_exception_handlers
from backend.database.connection import init_db

setup_logging()
settings = get_settings()
logger = get_logger(__name__)
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await _seed_demo_data()
    logger.info("startup_complete", version=settings.APP_VERSION,
                env=settings.ENVIRONMENT)
    yield
    logger.info("shutdown", service=settings.APP_NAME)


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── Middleware ─────────────────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Exception Handlers ─────────────────────────────────────────────────────
register_exception_handlers(app)

# ── Prometheus ─────────────────────────────────────────────────────────────
Instrumentator().instrument(app).expose(app, endpoint="/metrics")

# ── Routers ────────────────────────────────────────────────────────────────
from backend.api.v1.routers import auth, restaurants, orders, riders

app.include_router(auth.router)
app.include_router(restaurants.router)
app.include_router(orders.router)
app.include_router(riders.router)


# ── Health ─────────────────────────────────────────────────────────────────
@app.get("/health", tags=["System"])
async def health():
    return {
        "status": "ok",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
    }


# ── WebSocket ──────────────────────────────────────────────────────────────
@app.websocket("/ws/orders/{order_id}")
async def order_ws(websocket: WebSocket, order_id: int):
    from backend.websocket.manager import ws_manager
    await ws_manager.connect(websocket, order_id)
    try:
        while True:
            data = await websocket.receive_text()
            if data.strip() == "ping":
                await websocket.send_json({"event": "pong"})
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, order_id)


# ── Seed ───────────────────────────────────────────────────────────────────
async def _seed_demo_data():
    from backend.database.connection import AsyncSessionLocal
    from backend.models.restaurant import Restaurant, MenuItem
    from backend.models.user import User, UserRole
    from backend.auth.jwt_handler import hash_password
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(select(Restaurant).limit(1))
            if result.scalar_one_or_none():
                return

            seed_data = [
                {"name": "Spice Garden", "cuisine_type": "Indian",
                 "description": "Authentic North Indian curries",
                 "address": "MG Road, Bengaluru", "lat": 12.9756, "lng": 77.6010,
                 "avg_prep_time_minutes": 25, "rating": 4.5,
                 "menu": [("Butter Chicken", "Creamy tomato curry", 320, "Main"),
                          ("Garlic Naan", "Soft flatbread", 60, "Bread"),
                          ("Dal Makhani", "Black lentils", 220, "Main"),
                          ("Mango Lassi", "Sweet yogurt drink", 90, "Drinks")]},
                {"name": "Burger Barn", "cuisine_type": "American",
                 "description": "Gourmet smash burgers",
                 "address": "Koramangala, Bengaluru", "lat": 12.9352, "lng": 77.6245,
                 "avg_prep_time_minutes": 15, "rating": 4.3,
                 "menu": [("Classic Smash Burger", "Double patty, cheddar", 280, "Burgers"),
                          ("BBQ Bacon Burger", "Smoky BBQ sauce", 340, "Burgers"),
                          ("Loaded Fries", "Cheese sauce, jalapeños", 150, "Sides"),
                          ("Chocolate Shake", "Thick shake", 180, "Drinks")]},
                {"name": "Sushi Sensei", "cuisine_type": "Japanese",
                 "description": "Premium nigiri and rolls",
                 "address": "Indiranagar, Bengaluru", "lat": 12.9784, "lng": 77.6408,
                 "avg_prep_time_minutes": 30, "rating": 4.7,
                 "menu": [("Salmon Nigiri (6pc)", "Fresh salmon", 420, "Nigiri"),
                          ("Dragon Roll", "Prawn tempura, avocado", 520, "Rolls"),
                          ("Edamame", "Salted soybeans", 120, "Starters"),
                          ("Miso Soup", "Dashi broth", 80, "Soups")]},
                {"name": "Pasta Palace", "cuisine_type": "Italian",
                 "description": "Handmade pasta and pizza",
                 "address": "HSR Layout, Bengaluru", "lat": 12.9116, "lng": 77.6370,
                 "avg_prep_time_minutes": 20, "rating": 4.2,
                 "menu": [("Cacio e Pepe", "Roman pasta", 380, "Pasta"),
                          ("Margherita Pizza", "Buffalo mozzarella", 420, "Pizza"),
                          ("Tiramisu", "Espresso dessert", 220, "Desserts"),
                          ("Caesar Salad", "Romaine, parmesan", 280, "Salads")]},
            ]

            for rd in seed_data:
                menu = rd.pop("menu")
                r = Restaurant(**rd)
                db.add(r)
                await db.flush()
                for name, desc, price, cat in menu:
                    db.add(MenuItem(restaurant_id=r.id, name=name,
                                   description=desc, price=price, category=cat))

            for name, email, lat, lng, vehicle in [
                ("Arjun Kumar", "arjun@fusiondrop.in", 12.9716, 77.5946, "bike"),
                ("Priya Sharma", "priya@fusiondrop.in", 12.9600, 77.6200, "scooter"),
            ]:
                db.add(User(name=name, email=email,
                            hashed_password=hash_password("rider123"),
                            role=UserRole.rider, is_available=True,
                            current_lat=lat, current_lng=lng,
                            vehicle_type=vehicle))

            db.add(User(name="Demo Customer", email="demo@fusiondrop.in",
                        hashed_password=hash_password("demo1234"),
                        role=UserRole.customer))

            await db.commit()
            logger.info("seed_complete", message="Demo data seeded")
        except Exception as e:
            await db.rollback()
            logger.error("seed_error", error=str(e))