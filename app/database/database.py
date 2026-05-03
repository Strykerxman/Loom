from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import create_engine

SQLITE_DATABASE_URL = "sqlite:///./loom.db"

engine = create_engine(
    SQLITE_DATABASE_URL,
    connect_args={"check_same_thread": False}
    )

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_db():
    db: Session = SessionLocal() # create a new instance of the Session class, let's us perform transactions
    try:
        yield db
    finally:
        db.close()

    
