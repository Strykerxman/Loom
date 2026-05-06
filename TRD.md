# Loom – TRD (Remaining Work)

_Last updated: 2026-05-06_

## 0) Current Baseline (Done)
- Job/Task architecture with fan-out/fan-in
- FastAPI endpoints:
  - `POST /eval/start`
  - `GET /eval/status/{job_id}?include_tasks=`
- PostgreSQL + SQLAlchemy
- Worker with retry state machine (`pending -> running -> done|failed|pending`)
- `SKIP LOCKED` task claiming for multi-worker concurrency
- Python PII evaluator (email detection) + persisted `evaluation_result`
- Lightweight E2E script

---

## 1) Delivery Principle (Important)
Rust is a good fit for this project **only after** we stabilize contracts and prove evaluator bottlenecks with metrics.

**Rule:** No Rust implementation before Phase 2 exit criteria are met.

---

## 2) Prioritised Roadmap

## Phase 1 — Stabilise Core (P0)
Goal: eliminate fragility before adding new runtime components.

### 1.1 Worker session safety
- Use short-lived DB session per loop iteration (or per claimed task).
- Ensure `rollback()` on all exception paths.
- Prevent permanently stuck `running` tasks during normal failures.

**Acceptance**
- Worker runs 30+ min under load without transaction/session drift.

### 1.2 Status contract hardening
- Add `failed_tasks` to `JobResponse`.
- Keep aggregate counters sourced from DB counts, not task list length.
- Keep `tasks` optional payload via `include_tasks`.

**Acceptance**
- `completed_tasks + failed_tasks <= total_tasks` always true.

### 1.3 Migration discipline
- Introduce Alembic.
- Create initial migration from current models.
- Document migration commands in README.

**Acceptance**
- Fresh DB setup works from migrations only.

---

## Phase 2 — Functional Completeness (P1)
Goal: move from mock pipeline to product-capable pipeline.

### 2.1 LLM client abstraction
- Add `app/services/llm_client.py` interface.
- Support `mock` + one real provider (OpenAI or Anthropic) via env flags.
- Persist model metadata + latency in `TaskTable.response`.

**Acceptance**
- Worker can run in mock and real mode without code changes.

### 2.2 Expand evaluator coverage
- Add regex detectors: phone, SSN-like, credit-card-like.
- Keep deterministic output contract and dedupe/normalization.

**Acceptance**
- Unit tests for positive/negative cases per detector.

### 2.3 Crash recovery for `running` tasks
- Add task timestamps (`started_at`, `updated_at`).
- Add reaper job to requeue stale `running` tasks after TTL.

**Acceptance**
- Simulated worker crash does not orphan tasks.

---

## Phase 3 — Measure Before Rust (P1/P2 gate)
Goal: collect evidence that evaluator is the bottleneck.

### 3.1 Baseline benchmarks
- Measure:
  - tasks/sec
  - p95 task latency
  - worker CPU usage
  - evaluator time share
- Run with fixed prompt corpus and worker count.

**Acceptance (Rust gate)**
- Evaluator is a top bottleneck in profiles, not just DB/network wait.

---

## Phase 4 — Rust Performance Layer (P2)
Goal: implement Rust where it yields measurable ROI.

### 4.1 Rust sidecar (recommended first)
- Build Rust service for PII scanning (HTTP/gRPC).
- Keep same evaluator JSON contract:
  - `has_pii`, `types`, `matches`, `risk_score`
- Python worker calls sidecar instead of Python regex module.

**Why sidecar first**
- Clean boundary
- Easy rollback
- No Python ABI/build complexity initially

**Acceptance**
- ≥2x evaluator throughput improvement on same hardware
- No API/schema contract change
- No reliability regression

### 4.2 Optional in-process Rust (later)
- Consider PyO3/maturin only if sidecar overhead is significant.

---

## Phase 5 — Scale & Ops (P2/P3)
Goal: production readiness.

### 5.1 Structured logging + traceability
- Replace prints with structured logs.
- Include `job_id`, `task_id`, state transitions, retries, error class.

### 5.2 Pagination for task payloads
- Add `limit/offset` when `include_tasks=true`.
- Keep aggregate counts independent from pagination.

### 5.3 Optional queue broker
- Add Redis + Celery/ARQ if API enqueue pressure increases.
- Keep DB as source-of-truth for task state.

---

## 3) Lean Test Plan (must keep)
1. **Unit**: evaluator detectors + dedupe
2. **Integration**: POST/GET status contract + aggregate counters
3. **E2E**: API + worker + DB + retry behaviour
4. **Perf smoke**: baseline benchmark script (pre-Rust gate)

---

## 4) Immediate Next 3 Tasks (Do these next)
1. Add `failed_tasks` to API/schema + counts in GET status.
2. Refactor worker to short-lived session + rollback safety.
3. Add Alembic initial migration and migration docs.
