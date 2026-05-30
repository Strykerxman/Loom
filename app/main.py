from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .api import router

STATIC_DIR = Path(__file__).resolve().parent / "static"


app = FastAPI(
    title="Loom",
    description="Loom is a high-throughput, distributed evaluation pipeline designed to stress-test LLM reliability, PII leakage, and hallucination rates through a resilient Job/Task architecture.",
)


@app.get("/")
def root():
    return {"message": "Welcome to Loom, your LLM evaluation pipeline."}


@app.get("/demo", include_in_schema=False)
def demo():
    return FileResponse(STATIC_DIR / "demo.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.include_router(router)
