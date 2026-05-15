# backend/main.py
"""
FusionDrop Backend — FastAPI Application Entry Point
------------------------------------------------------
Run:  uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
Docs: http://localhost:8000/docs
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from backend.core.config import settings
from backend.core.logging_config import setup_logging
from backend.database.connection import init_db, SessionLocal
from backend.middleware.error_handler import app_exception_handler
from backend.middleware.request_id import RequestContextMiddleware
from backend.core.exceptions import AppException
from backend.models.restaurant import Restaurant, MenuItem
from backend.models.user import User, UserRole
from backend.auth.jwt_handler import hash_password
from backend.routers import auth, restaurants, orders, riders
from backend.schemas.common import ApiResponse
from backend.websocket.manager import ws_manager

# Configure logging once at import time
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Database initialisation
    init_db()
    await _seed_demo_data()
    logger.info("✅ FusionDrop API ready — http://localhost:8000/docs")
    yield


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    lifespan=lifespan,
    debug=settings.debug,
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestContextMiddleware)

# Exception handlers
app.add_exception_handler(AppException, app_exception_handler)

# Routers
app.include_router(auth.router)
app.include_router(restaurants.router)
app.include_router(orders.router)
app.include_router(riders.router)


@app.get("/health", tags=["System"], response_model=ApiResponse[dict])
def health():
    return ApiResponse(
        data={
            "status": "ok",
            "service": "FusionDrop",
            "version": app.version,
            "env": settings.env,
        }
    )


@app.websocket("/ws/orders/{order_id}")
async def order_ws(websocket: WebSocket, order_id: int):
    await ws_manager.connect(websocket, order_id)
    try:
        while True:
            data = await websocket.receive_text()
            if data.strip() == "ping":
                await websocket.send_json({"event": "pong"})
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, order_id)


async def _seed_demo_data():
    """
    Seeds demo restaurants and users if the DB is empty.

    Kept intentionally simple and synchronous since it runs once on startup.
    """
    db = SessionLocal()
    try:
        if db.query(Restaurant).count() > 0:
            return

        restaurant_payloads = [
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
                    ("Edamame", "Salted soybeans", 120, "Starters"),
                    ("Miso Soup", "Dashi broth", 80, "Soups"),
                ],
            },
            {
                "name": "Pasta Palace",
                "cuisine_type": "Italian",
                "description": "Handmade pasta and pizza",
                "address": "HSR Layout, Bengaluru",
                "lat": 12.9116,
                "lng": 77.6370,
                "avg_prep_time_minutes": 20,
                "rating": 4.2,
                "menu": [
                    ("Cacio e Pepe", "Roman pasta", 380, "Pasta"),
                    ("Margherita Pizza", "Buffalo mozzarella", 420, "Pizza"),
                    ("Tiramisu", "Espresso dessert", 220, "Desserts"),
                    ("Caesar Salad", "Romaine, parmesan", 280, "Salads"),
                ],
            },
        ]

        for rd in restaurant_payloads:
            menu = rd.pop("menu")
            r = Restaurant(**rd)
            db.add(r)
            db.flush()
            for name, desc, price, cat in menu:
                db.add(
                    MenuItem(
                        restaurant_id=r.id,
                        name=name,
                        description=desc,
                        price=price,
                        category=cat,
                    )
                )

        for name, email, lat, lng, vehicle in [
            ("Arjun Kumar", "arjun@fusiondrop.in", 12.9716, 77.5946, "bike"),
            ("Priya Sharma", "priya@fusiondrop.in", 12.9600, 77.6200, "scooter"),
        ]:
            db.add(
                User(
                    name=name,
                    email=email,
                    hashed_password=hash_password("rider123"),
                    role=UserRole.rider,
                    is_available=True,
                    current_lat=lat,
                    current_lng=lng,
                    vehicle_type=vehicle,
                )
            )

        db.add(
            User(
                name="Demo Customer",
                email="demo@fusiondrop.in",
                hashed_password=hash_password("demo1234"),
                role=UserRole.customer,
            )
        )

        db.commit()
        logger.info("✅ Demo data seeded.")
    except Exception as e:
        db.rollback()
        logger.error(f"Seed error: {e}")
    finally:
        db.close()