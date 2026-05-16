import os
from functools import lru_cache
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import load_env


FALLBACK_DATABASE_URL = "sqlite:///./fallback.db"


def get_database_url() -> str:
    load_env()
    return os.getenv("DATABASE_URL", FALLBACK_DATABASE_URL)


def create_session_factory(database_url: str | None = None):
    engine = create_engine(database_url or get_database_url())
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)


@lru_cache(maxsize=1)
# Creating database engines is computationally expensive and establishes network connection pools. 
# This cache ensures the engine and pool are created exactly once and reused globally.
def get_session_factory():
    return create_session_factory()


def reset_session_factory_cache() -> None:
    get_session_factory.cache_clear()


def get_db():
    """
    Dependency function to get a database session for API endpoints.
    Ensures that the session is properly closed after the request is done.
    """
    SessionLocal = get_session_factory()
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
