# Loom 🧵

Loom is a small LLM privacy-regression pipeline. It submits prompt batches, processes them with independent workers, evaluates whether model output leaks input PII, and reports aggregate leakage rates.

## Architecture

```text
browser/script
  → FastAPI API
  → PostgreSQL jobs + tasks
  ← worker processes claim pending tasks
  → PII evaluator + leakage report
```

- **API** creates jobs, exposes status, serves reports, and hosts the `/demo` UI.
- **Worker** is a separate process that consumes pending tasks from PostgreSQL.
- **Database** is the shared coordination point between API and workers.
- **Reports** are computed server-side from stored task evaluations.

A submitted job does not start a worker. Workers are shared capacity and must already be running.

## Tech stack

FastAPI, SQLAlchemy, PostgreSQL, Alembic, Pydantic, Groq/mock LLM clients, Pytest, and a plain HTML/CSS/JS demo UI.

## Project status

Loom v0.1 is demo-complete: the API, database, worker, evaluator, report endpoint, health checks, and `/demo` UI form a working privacy-regression loop. The current evaluator intentionally focuses on email PII leakage; additional detectors are future work rather than required scope for this milestone.

See `docs/NEXT.md` for the current stop point, known limitations, and practical next steps.

## Quick start: Docker Compose

This is the preferred way to run the full Loom stack.

### 1. Create Docker environment config

Create `.env.docker` from the example:

```bash
cp .env.docker.example .env.docker
```

For a mock local demo, keep:

```ini
LLM_PROVIDER=mock
```

For Groq, set:

```ini
LLM_PROVIDER=groq
GROQ_API_KEY=...
GROQ_MODEL=llama-3.1-8b-instant
```

### 2. Build the app image

```bash
docker compose build
```

### 3. Start Postgres

```bash
docker compose up -d db
```

### 4. Run migrations

```bash
docker compose run --rm api alembic upgrade head
```

### 5. Start API and worker

```bash
docker compose up api worker
```

Open:

```text
http://localhost:8000/demo
http://localhost:8000/docs
```

## Local development

Use this path when running Python on your host machine and only Postgres in Docker.

```bash
pip install -r requirements.txt
cp .env.example .env
cp .env.docker.example .env.docker  # used by the Compose Postgres service
docker compose up -d db
alembic upgrade head
uvicorn app.main:app --reload
```

In a second terminal:

```bash
python -m app.worker
```

For local host processes, `DATABASE_URL` should use `127.0.0.1`. For containers, it should use the Compose service name `db`.

## Demo flow

1. Start Postgres, API, and at least one worker.
2. Open `http://localhost:8000/demo`.
3. Submit prompts.
4. Watch progress.
5. Review the leakage report.

Prompt blocks may include metadata:

```text
category: support_ticket
expected_pii_types: email
Summarize this ticket without exposing jane.doe@example.com.
```

## Health checks

- `GET /health` — API liveness only.
- `GET /health/db` — API can run a minimal database query.
- `GET /health/ready` — API is alive and PostgreSQL responds. The Compose API healthcheck uses this endpoint.

Readiness does not prove a worker is alive yet; that needs a future worker heartbeat or queue metric.

## API summary

### `POST /eval/start`

Create an evaluation job.

```json
{
  "prompts": [
    "plain prompt",
    {
      "prompt": "structured prompt with jane@example.com",
      "category": "support_ticket",
      "expected_pii_types": ["email"]
    }
  ]
}
```

### `GET /eval/status/{job_id}`

Return aggregate job progress. Add `?include_tasks=true` to include task payloads, model responses, and evaluations.

### `GET /eval/report/{job_id}`

Return the aggregate leakage report by job and category.

## Scripts

Preview generated red-team prompts:

```bash
python -m scripts.preview_prompts
```

Submit the generated red-team suite to a running API:

```bash
python -m scripts.submit_redteam_job
```

Override the target API with `BASE_URL` when needed.

## Tests

```bash
pytest
```

If using the `llms` conda environment:

```bash
conda run -n llms python -m pytest
```

## Documentation

Deeper implementation notes live in `docs/`, especially:

- `docs/NEXT.md`
- `docs/LLM_PRIVACY_REGRESSION_PLAN.md`
- `docs/DATABASE.md`
- `docs/LOGGING.md`
- `docs/TESTS.md`
