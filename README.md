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

**Current (Phase 1 & 2: Distributed Foundation)**
* **Web Framework:** FastAPI
* **ORM & Database:** SQLAlchemy + PostgreSQL (Local Docker)
* **Data Validation:** Pydantic
* **Evaluation Engine:** Isolated Python service (Regex-based PII detection)

**Roadmap (Phase 3: LLM Integration)**
* **Message Broker:** Redis + Celery (Optional Task Queueing upgrade)
* **AI Integration:** OpenAI / Anthropic SDK for prompt execution

## 🚀 Getting Started

### Prerequisites
* Python 3.10+
* Virtual Environment (recommended)

### Installation
1. Clone the repository and navigate to the root directory.  
2. Install dependencies:
   ```bash
   pip install fastapi uvicorn sqlalchemy pydantic dotenv pydantic-settings psycopg2-binary
   ```  
3. Start the application:
   ```bash
   uvicorn app.main:app --reload
   ```  
4. Access the interactive API documentation at: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)  

5. Start the Postgres Docker container:
   ```bash
   docker-compose up -d
   ```
   ***NOTE***: Copy `.env.example` to `.env` and keep the local `.env` untracked.
6. Create a simple POST request to start a job:
   ```bash
      curl -X 'POST' \
      'http://127.0.0.1:8000/eval/start' \
      -H 'accept: application/json' \
      -H 'Content-Type: application/json' \
      -d '{
         "prompts": [
            "p1", "p2", "p3", "p4", "p5", "p6", "p7", "p8", "p9", "p10", "p11", "p12", "p13", "p14", "p15", "p16", "p17", "p18", "p19", "p20"
         ]
      }'
   ```
   ***NOTE***: The current implementation mocks LLM responses by using `time.sleep(2)`. **No API calls are being made yet.**  

7. Deploy workers from the command prompt from the source directory (you may launch as many as desired):
   ```bash
   cd path/to/Loom
   python -m app.worker
   ```

## 🔌 API Reference

### `POST /eval/start`
Submit a batch of prompts for evaluation. Returns a Claim Ticket (`job_id`) and task counts.
* **Payload:** `{"prompts": ["prompt 1", "prompt 2"]}`
* **Response:** `202 Accepted` | `{"job_id": 1, "status": "pending", "tasks": [], "total_tasks": 2, "completed_tasks": 0}`

### `GET /eval/status/{job_id}`
Check the aggregate status of an existing evaluation job and its underlying tasks.
* **Query Parameters:** `?include_tasks=true` (optional, defaults to false)
* **Response (include_tasks=false):** `200 OK` | `{"job_id": 1, "status": "running", "tasks": [], "total_tasks": 2, "completed_tasks": 1}`
* **Response (include_tasks=true):** `200 OK` | `{"job_id": 1, "status": "done", "tasks": [{"task_id": 1, "status": "done", "payload": {"prompt": "prompt 1"}, "response": {"text": "Echo: prompt 1", "model": "mock-llm"}, "evaluation_result": {"has_pii": false, "types": [], "matches": {}, "risk_score": 0.0}, "error_log": null}], "total_tasks": 2, "completed_tasks": 2}`
* **Errors:** `404 Not Found` if the job does not exist.

---
*Built with a focus on Responsible AI and Financial Compliance.*