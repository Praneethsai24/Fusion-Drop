# backend/database/connection.py
"""
Database Connection
--------------------
SQLAlchemy engine, session factory, and table initialisation.
Uses SQLite for the MVP; swap DATABASE_URL for Postgres in production.
"""

import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from backend.core.config import settings

logger = logging.getLogger(__name__)

DATABASE_URL = settings.database_url

# SQLite needs check_same_thread=False for FastAPI's thread model
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    echo=False,  # set True for SQL query logging during debug
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency — yields a DB session and closes it after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables defined in the models. Safe to call multiple times."""
    # Import models so SQLAlchemy registers their metadata before create_all
    from backend.models import user, restaurant, order  # noqa: F401

    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created / verified.")