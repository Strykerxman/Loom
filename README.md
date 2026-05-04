# Loom 🧵

> **A high-throughput, distributed evaluation pipeline designed to stress-test LLM reliability, PII leakage, and hallucination rates through a resilient Job/Task architecture.**

---

## 📖 Overview

Evaluating Large Language Models (LLMs) at scale presents a unique infrastructure challenge: LLM APIs rate-limit, timeout, and fail unpredictably. Attempting to process 10,000 prompts synchronously is a recipe for data loss and wasted compute.

**Loom** solves this by decoupling the *Intent* (the Job) from the *Execution* (the Tasks). It utilizes a robust **Fan-Out / Fan-In** architecture to isolate failures. If prompt #8,999 triggers an OpenAI rate limit, the isolated task simply pauses and retries. The rest of the pipeline continues uninterrupted, guaranteeing 99.9% persistence and zero blast radius.

## 🏗️ Architecture: The "Claim Ticket" Pattern

Loom operates asynchronously. When a client submits a batch of prompts, the API does not block waiting for the LLM to respond. 

1. **Fan-Out:** The API instantly registers a global `Job` and chunks the payload into individual `Tasks` stored in the database.
2. **The Receipt:** The API immediately returns an `HTTP 202 Accepted` with a `job_id` (the claim ticket).
3. **Execution (Workers):** Background workers independently pull tasks, execute LLM calls, run PII/Hallucination evaluations, and update the task status.
4. **Fan-In:** The client uses the `job_id` to poll the API, retrieving the aggregated results once all tasks complete.

## 💻 Tech Stack

**Current (Phase 1: Foundation)**
* **Web Framework:** FastAPI
* **ORM & Database:** SQLAlchemy + SQLite (Local Prototyping)
* **Data Validation:** Pydantic

**Roadmap (Phase 2 & 3: Distributed Execution)**
* **Database:** PostgreSQL (for row-level locking and concurrency)
* **Message Broker:** Redis + Celery (Task Queueing)
* **High-Performance Workers:** Rust (Regex-based PII scrubbing engine)

## 🚀 Getting Started

### Prerequisites
* Python 3.10+
* Virtual Environment (recommended)

### Installation
1. Clone the repository and navigate to the root directory.
2. Install dependencies:
   ```bash
   pip install fastapi uvicorn sqlalchemy pydantic
   ```
3. Start the application:
   ```bash
   uvicorn app.main:app --reload
   ```
4. Access the interactive API documentation at: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

## 🔌 API Reference

### `POST /evaluate/eval`
Submit a batch of prompts for evaluation. Returns a Claim Ticket (`job_id`).
* **Payload:** `{"prompts": ["prompt 1", "prompt 2"]}`
* **Response:** `202 Accepted` | `{"job_id": 1, "status": "pending"}`

### `GET /evaluate/status/{job_id}`
Check the status of an existing evaluation job.
* **Response:** `200 OK` | `{"job_id": 1, "status": "running"}`
* **Errors:** `404 Not Found` if the job does not exist.

---
*Built with a focus on Responsible AI and Financial Compliance.*