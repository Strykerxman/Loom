from contextlib import asynccontextmanager
from fastapi import FastAPI
from .api import router
from .database.database import init_db
from .models.base import Base
from .models import models


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()

    from .database.database import engine
    Base.metadata.create_all(bind=engine)

    yield
    # engine = None when importing engine from .database.database; init_db() has not been called yet.
    # init_db() is called, engine is no longer None, so we import it and bind it.
    # Note: we can make init_db *return* the engine instead
    

app = FastAPI(
    title="Loom",
    description="Loom is a high-throughput, distributed evaluation pipeline designed to stress-test LLM reliability, PII leakage, and hallucination rates through a resilient Job/Task architecture.",
    lifespan=lifespan
)


@app.get("/")
def root():
    return {"message": "Welcome to Loom, your LLM evaluation pipeline."}


app.include_router(router)