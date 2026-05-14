### Test layers

Keep the fast path boring:

```bash
pytest
```

By default, full-stack E2E tests are skipped. They start Uvicorn/workers and are intentionally opt-in:

```bash
pytest --run-e2e tests/test_e2e.py -s
```

Database-backed tests that use `db_session` still start the test Postgres container from `docker-compose.test.yml`, wait for readiness, and run `alembic upgrade head` automatically.

Your local `.env.test` should match the test compose file:

```env
DATABASE_URL=postgresql://loom_test:loom_pw@127.0.0.1:5433/loom_test_db
DATABASE_PASSWORD=loom_pw
BASE_URL=http://127.0.0.1:8001
```

Keep the test Postgres container/volume after pytest exits:

```bash
KEEP_TEST_STACK=1 pytest
```

Otherwise pytest tears the test stack down with `docker compose -f docker-compose.test.yml down -v`.

### Where the test plumbing lives

The ugly Docker/Uvicorn/process orchestration is intentionally quarantined in:

```text
tests/support/test_stack.py
```

`tests/conftest.py` should stay as a small fixture wiring layer.

### End-to-End (E2E) Integration Test

Because *Loom* is a distributed, asynchronous system, traditional unit tests aren't sufficient to validate the entire workflow. Instead, we have an E2E test that simulates a real client interaction with the API, from job submission to result retrieval. This test ensures that all components of the system (API, database, workers) are working together correctly.

The current test in `tests/test_e2e.py` follows this logic:

1. **Job Submission (Fan-Out):** The test acts like a client, submits a batch of prompts to the `POST /eval/start` endpoint and receives a `job_id` claim ticket in return.
2. **Async Polling:** Workers process tasks independently. The test polls `GET /eval/status/{job_id}?include_tasks=false` until the job is terminal.
3. **Result Validation (Fan-In):** The test fetches `include_tasks=true`, checks task results, and verifies the aggregate counters are sane.
