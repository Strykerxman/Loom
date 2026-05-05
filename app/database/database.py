import os
from dotenv import load_dotenv
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import create_engine

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./fallback.db")

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_db():
    """
    Dependency function to get a database session for API endpoints.
    Ensures that the session is properly closed after the request is done.
    """
    db: Session = SessionLocal() # Create a new instance of the Session class, let's us perform transactions
    try:
        yield db
    finally:
        db.close()