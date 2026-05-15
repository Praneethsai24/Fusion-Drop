"""
FusionDrop – Centralised configuration via Pydantic-Settings.
All values resolved from environment / .env file on startup.
"""
from functools import lru_cache
from typing import List
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    APP_NAME: str = "FusionDrop"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://fusiondrop:fusiondrop@localhost:5432/fusiondrop"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Auth
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_origins(cls, v):
        if isinstance(v, str):
            return [o.strip() for o in v.split(",")]
        return v

    # OpenAI
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"

    # Delivery optimiser constants (were hardcoded — now configurable)
    BATCH_RADIUS_KM: float = 3.0
    BASE_DELIVERY_FEE: float = 30.0
    FEE_PER_KM: float = 8.0
    BATCH_DISCOUNT: float = 0.25
    AVG_RIDER_SPEED_KMH: float = 25.0
    STOP_BUFFER_MINS: int = 3

    # Cache TTLs (seconds)
    CACHE_TTL_RESTAURANTS: int = 300
    CACHE_TTL_RECOMMENDATIONS: int = 600
    CACHE_TTL_OPTIMIZATION: int = 60


@lru_cache
def get_settings() -> Settings:
    return Settings()