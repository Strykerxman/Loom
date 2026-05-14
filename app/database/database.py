import os

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import load_env


load_env()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./fallback.db")

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_db():
    """
    Dependency function to get a database session for API endpoints.
    Ensures that the session is properly closed after the request is done.
    """
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
