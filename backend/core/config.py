"""
FusionDrop — Centralised configuration via Pydantic-Settings.
All values are resolved from environment variables or the .env file on startup.
"""
import secrets
from functools import lru_cache
from typing import List

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ───────────────────────────────────────────────────────────────────
    APP_NAME: str = "FusionDrop"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"

    # ── Database ──────────────────────────────────────────────────────────────
    DATABASE_URL: str = (
        "postgresql+asyncpg://fusiondrop:fusiondrop@localhost:5432/fusiondrop"
    )

    # ── Redis ─────────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── Auth ──────────────────────────────────────────────────────────────────
    # IMPORTANT: Override SECRET_KEY in production.
    # Generate one with: python -c "import secrets; print(secrets.token_hex(32))"
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── CORS ──────────────────────────────────────────────────────────────────
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
    ]

    # ── OpenAI / LLM ─────────────────────────────────────────────────────────
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"

    # ── Delivery optimiser constants ──────────────────────────────────────────
    BATCH_RADIUS_KM: float = 3.0
    BASE_DELIVERY_FEE: float = 30.0
    FEE_PER_KM: float = 8.0
    BATCH_DISCOUNT: float = 0.25
    AVG_RIDER_SPEED_KMH: float = 25.0
    STOP_BUFFER_MINS: int = 3

    # ── Cache TTLs (seconds) ─────────────────────────────────────────────────
    CACHE_TTL_RESTAURANTS: int = 300
    CACHE_TTL_RECOMMENDATIONS: int = 600
    CACHE_TTL_OPTIMIZATION: int = 60

    # ── Validators ────────────────────────────────────────────────────────────

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_origins(cls, v: object) -> List[str]:
        """Accept comma-separated string or a list."""
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v  # type: ignore[return-value]

    @field_validator("SECRET_KEY", mode="after")
    @classmethod
    def secret_key_min_length(cls, v: str) -> str:
        """Enforce minimum key entropy in all environments."""
        if len(v) < 32 and v != "change-me-in-production":
            raise ValueError(
                "SECRET_KEY must be at least 32 characters. "
                "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
            )
        return v

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        """
        Hard-fail if production is started with the default insecure secret key.
        This prevents the most common misconfiguration that leads to forged JWTs.
        """
        if self.ENVIRONMENT == "production":
            if self.SECRET_KEY == "change-me-in-production":
                raise ValueError(
                    "\n\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    "  FATAL: SECRET_KEY is set to the insecure default value.\n"
                    "  All JWTs are forgeable. The server will NOT start.\n"
                    "\n"
                    "  Fix: set SECRET_KEY in your .env or environment:\n"
                    "  python -c \"import secrets; print(secrets.token_hex(32))\"\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                )
            if self.DEBUG:
                raise ValueError(
                    "DEBUG=true is not allowed in ENVIRONMENT=production."
                )
        return self

    def generate_secret_key(self) -> str:  # noqa: D102 — utility helper
        """Convenience method to generate a secure key."""
        return secrets.token_hex(32)


@lru_cache
def get_settings() -> Settings:
    return Settings()