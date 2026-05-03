from contextlib import asynccontextmanager
from fastapi import FastAPI
from .api import router
from .database.database import engine
from .models.base import Base
from .models import models


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield
    

app = FastAPI(
    title="Loom",
    description="Loom is a high-throughput, distributed evaluation pipeline designed to stress-test LLM reliability, PII leakage, and hallucination rates through a resilient Job/Task architecture.",
    lifespan=lifespan
)


@app.get("/")
def root():
    return {"message": "Welcome to Loom, your LLM evaluation pipeline."}


app.include_router(router)