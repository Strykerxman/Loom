# Loom Next Steps

This document marks Loom's current stop point and preserves the next useful directions for future work.

## Current milestone: v0.1 demo-complete

Loom now demonstrates the core privacy-regression pipeline:

```text
prompt batch
  -> FastAPI API
  -> PostgreSQL jobs/tasks
  -> independent worker
  -> LLM/mock provider
  -> PII evaluator
  -> leakage report + demo UI
```

The project is intentionally scoped around **email PII leakage** for now. More detectors are future expansion, not required to prove the architecture.

## What works

- API endpoints for starting jobs, checking status, and fetching reports.
- A static `/demo` UI for submitting prompts and viewing leakage reports.
- PostgreSQL-backed job/task coordination.
- A worker process/container that claims pending tasks and evaluates responses.
- Mock and Groq-backed LLM clients.
- Email and obfuscated-email PII detection.
- Server-side leakage reporting by job and category.
- Docker Compose services for API, worker, and database.
- Health endpoints for API liveness, DB reachability, and API readiness.
- Tests for payloads, workers, reports, health checks, evaluator behavior, timestamps, and prompt generation.

## Known limitations

- Worker health is inferred from job progress/logs; there is no heartbeat table yet.
- Readiness proves API + DB, not that workers are actively consuming tasks.
- `jobs.status` is kept in sync during normal task transitions, but task status remains the source of truth for progress calculations.
- Only email-style PII is detected.
- The mock LLM is intentionally simple and deterministic for demos.
- There is no stale-running-task reaper or lease renewal model yet.
- There is no central rate limiter for real provider calls.

## Good next features

### 1. Worker observability

Add lightweight queue/worker visibility before adding autoscaling:

- pending task count
- running task count
- failed task count
- oldest pending task age
- optional worker heartbeat

A future endpoint could be:

```text
GET /eval/queue
```

### 2. One additional detector

If expanding evaluator coverage, add **phone number detection** before more complex PII types. Phone numbers already appear in some generated prompts, and they are a natural second detector after email.

Avoid jumping straight to names or addresses; those have much harder false-positive behavior.

### 3. Stale running task recovery

Only after worker visibility exists, add a reaper for tasks stuck in `running` too long.

Important model:

```text
pending tasks are not lost
stale running tasks are the recovery target
```

### 4. Reporting polish

Keep report logic server-owned. UI improvements should visualize existing report data, not recalculate leakage in JavaScript.

Useful additions:

- category sorting
- failure-rate display
- provider/model summary
- export report JSON button

## Small Pythonic refactor candidates

These are optional cleanup ideas if you want to practice using Python more idiomatically before parking the project.

### Move domain rules out of the app root

Current:

```text
app/status_rules.py
```

Possible future home:

```text
app/domain/job_status.py
```

Why: the rule is business/domain logic, not API, DB, or worker plumbing.

### Use `defaultdict(list)` when grouping PII matches

In `app/services/evaluator.py`, match grouping is currently manual. Python's `collections.defaultdict` is often cleaner for grouping.

Unrelated example:

```python
from collections import defaultdict

orders_by_customer = defaultdict(list)

for order in orders:
    orders_by_customer[order.customer_id].append(order)
```

Why it is good: grouping is a common Python pattern, and `defaultdict(list)` removes repetitive "if key missing" code.

When it is overkill: if there are only one or two assignments and readability is already obvious.

### Use small pure functions for repeated response shapes

In `app/api/endpoints/health.py`, healthy and unhealthy response shapes are repeated.

Unrelated example:

```python
def ok_check(name: str) -> dict[str, str]:
    return {name: "ok"}
```

Why it is good: when response structures repeat, helper functions reduce drift.

When it is overkill: if the repetition is still clearer than abstraction. Health endpoints should stay boring.

### Prefer comprehensions when they directly express a transformation

`app/services/redteam_prompts.py` builds a list by appending in a loop. A list comprehension could be more direct.

Unrelated example:

```python
names = [user.name for user in users]
```

Why it is good: it says "this list is just a transformation." That is Pythonic and readable.

When it is overkill: avoid very long comprehensions with nested conditions or side effects.

### Consider `match` only for real branching clarity

`app/services/llm_client.py` currently has simple provider branching. Python's `match` statement exists, but it would not necessarily improve this yet.

Unrelated example where `match` helps:

```python
match event["type"]:
    case "user.created":
        handle_user_created(event)
    case "user.deleted":
        handle_user_deleted(event)
    case _:
        ignore(event)
```

Why it is good: it reads well when there are many named cases.

Why it may be overkill here: `if provider == "groq"` is simpler while there are only two provider paths.

### Use constants for repeated status strings only when repetition grows

Status values currently appear across schemas, CRUD, and worker code. A future enum or constants module could reduce typo risk.

Unrelated example:

```python
PENDING = "pending"
RUNNING = "running"
DONE = "done"
```

Why it is good: repeated string contracts are easy to mistype.

Why it may be overkill now: Pydantic `Literal` types already document the allowed status values, and too many constants can make simple code feel ceremonial.

## Things intentionally deferred

- Autoscaling workers.
- Per-job worker spawning.
- Production auth.
- Multi-tenant user accounts.
- Full provider rate-limit management.
- Rich frontend framework migration.
- Detector garden expansion.

## Recommended parking checklist

Before moving on, do one final manual validation:

```bash
docker compose build
docker compose up -d db
docker compose run --rm api alembic upgrade head
docker compose up api worker
```

Then verify:

```text
http://localhost:8000/health
http://localhost:8000/health/db
http://localhost:8000/health/ready
http://localhost:8000/demo
```

If that path works, Loom is in a reasonable v0.1 stopping state.
