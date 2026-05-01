from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session
from sqlalchemy import create_engine, Engine

SQLITE_DATABASE_URL = "sqlite:///./sentinel.db"
engine: Engine = None
SessionLocal: Session = None

# engine = create_engine(
#     SQLITE_DATABASE_URL,
#     connect_args={"check_same_thread": False}
#     )

# SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

class Base(DeclarativeBase):
    pass


def init_db():
    global engine, SessionLocal

    if engine is None:

        engine = create_engine(
            SQLITE_DATABASE_URL,
            connect_args={"check_same_thread": False}
        )

        SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

def get_db():

    if SessionLocal is None:
        init_db()

    db: Session = SessionLocal() # create a new instance of the Session class, let's us perform transactions

    try:
        yield db
        
    finally:
        db.close()

    
