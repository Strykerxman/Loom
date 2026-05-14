from fastapi import FastAPI

from .api import router


app = FastAPI(
    title="Loom",
    description="Loom is a high-throughput, distributed evaluation pipeline designed to stress-test LLM reliability, PII leakage, and hallucination rates through a resilient Job/Task architecture.",
)


@app.get("/")
def root():
    return {"message": "Welcome to Loom, your LLM evaluation pipeline."}


app.include_router(router)
