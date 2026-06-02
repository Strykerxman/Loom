# Robust Python Notes

A running checklist of small Python architecture/testing lessons worth carrying into future projects.

## 1. Keep `conftest.py` fixture-focused

Use `tests/conftest.py` for pytest fixtures and global test setup only:

- database/session fixtures
- app/client fixtures
- environment setup
- monkeypatch defaults

Avoid dumping random helper functions into `conftest.py`. If helpers are normal functions, put them in an explicit helper module instead.

Good pattern:

```text
tests/
  conftest.py        # fixtures only
  factories.py       # create/fetch test records
  helpers.py         # generic test helpers
```

Example:

```python
# tests/factories.py
from sqlalchemy.orm import Session

from app.database import crud
from app.models import TaskTable


def get_task(db_session: Session, task_id: int) -> TaskTable:
    db_session.expire_all()
    return db_session.query(TaskTable).filter(TaskTable.task_id == task_id).one()


def create_single_task(db_session: Session, prompt: str = "hello") -> TaskTable:
    job = crud.create_eval_job(db_session, [prompt])
    return (
        db_session.query(TaskTable)
        .filter(TaskTable.parent_job_id == job.job_id)
        .one()
    )
```

Then import explicitly:

```python
from tests.factories import create_single_task, get_task
```

## 2. `scripts/` should not contain app/domain logic

`scripts/` is for runnable/dev/ops helpers, not core runtime behavior.

If API/runtime code imports from `scripts`, that is usually a smell:

```python
# avoid
from scripts.job_status import derive_job_status
```

Prefer app-owned modules:

```python
from app.status_rules import derive_job_status
```

Rule of thumb:

- `scripts/`: CLI helpers, dev utilities, one-off jobs
- `app/services/`: reusable app/business logic
- `app/api/`: HTTP boundary
- `app/database/`: persistence access
- `tests/`: tests and test-only helpers

## 3. Import-time side effects are footguns

This pattern is convenient but fragile:

```python
load_env()
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
```

Why? Because `engine` is created at import time. If tests set `ENV_FILE` after importing the module, it is too late.

This works only if env is configured before import:

```python
os.environ.setdefault("ENV_FILE", ".env.test")
load_env(override=True)

from app.database.database import SessionLocal
```

More robust long-term pattern: use factories/injection so configuration is read when constructing dependencies, not accidentally during import.

```python
def create_session_factory(database_url: str):
    engine = create_engine(database_url)
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)
```

## 4. Make destructive tests prove they are using a test database

If a fixture truncates or deletes data, guard it hard:

```python
def _assert_test_database() -> None:
    database_url = os.getenv("DATABASE_URL", "")

    if "test" not in database_url.lower():
        raise RuntimeError("Refusing to run destructive cleanup against a non-test database.")
```

This is cheap insurance against accidentally nuking local/dev/prod data.

## 5. Pytest discovery depends on names

Pytest only auto-discovers tests named like:

```python
def test_something():
    ...
```

A function like this is just a manual script entrypoint, not a pytest test:

```python
def run_e2e_test():
    ...
```

That can be fine, but be intentional. If it should run under pytest, wrap it:

```python
def test_e2e_pipeline():
    run_e2e_test()
```

## 6. Put contract logic behind small pure functions

If business/API semantics are important, isolate them in small pure functions and test them directly.

Example:

```python
def derive_job_status(*, total_tasks: int, running_tasks: int, terminal_tasks: int) -> JobStatus:
    if total_tasks <= 0:
        return "pending"
    if terminal_tasks >= total_tasks:
        return "done"
    if running_tasks > 0 or terminal_tasks > 0:
        return "running"
    return "pending"
```

Benefits:

- easier tests
- fewer API endpoint branches
- clearer contract
- safer refactors

## 7. Timebox tests to preserve momentum

When tests feel like they are killing momentum, do not disappear into a giant coverage cleanup.

Use a small testing tax:

1. Add tests for the riskiest contract or bug-prone logic.
2. Add tests around code you are about to build on.
3. Defer exhaustive coverage to a TODO/issue.
4. Move on.

Good examples before adding new provider/red-team/faker features:

- evaluator output contract
- job status derivation
- worker success/failure state transitions
- API status counters

## 8. Prefer explicit boundaries

A robust Python project is easier to reason about when each layer has a clear job:

```text
app/api/       HTTP request/response boundary
app/services/  business logic, provider abstractions, evaluators
app/database/  DB sessions and CRUD helpers
app/models/    ORM models
app/schemas/   Pydantic/API contracts
scripts/       operational/dev scripts only
tests/         tests, fixtures, factories
```

When unsure where code belongs, ask: "Will the app import this at runtime?" If yes, it probably belongs under `app/`, not `scripts/`.
