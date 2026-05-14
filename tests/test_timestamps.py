from sqlalchemy.orm import Session
from app.database import crud
from app.models import TaskTable


def _get_task(db_session: Session, task_id: int) -> TaskTable:
    db_session.expire_all()
    return db_session.query(TaskTable).filter(TaskTable.task_id == task_id).one()


def _create_single_task(db_session: Session) -> TaskTable:
    job = crud.create_eval_job(db_session, ["hello"])
    return (
        db_session.query(TaskTable)
        .filter(TaskTable.parent_job_id == job.job_id)
        .one()
    )


def test_created_task_has_created_and_updated_timestamps(db_session: Session):
    task = _create_single_task(db_session)

    assert task.status == "pending"
    assert task.created_at is not None
    assert task.updated_at is not None
    assert task.started_at is None
    assert task.completed_at is None


def test_running_task_has_started_timestamp(db_session):
    task = _create_single_task(db_session)

    crud.mark_task_running(db_session, task.task_id)
    task = _get_task(db_session, task.task_id)

    assert task.status == "running"
    assert task.started_at is not None
    assert task.updated_at is not None
    assert task.completed_at is None


def test_done_task_has_completed_timestamp(db_session):
    task = _create_single_task(db_session)

    crud.mark_task_running(db_session, task.task_id)
    crud.mark_task_as_done(
        db_session,
        task.task_id,
        response={"text": "ok", "model": "mock", "latency_ms": 1},
        pii_eval={"has_pii": False, "types": [], "matches": {}, "risk_score": 0.0},
    )
    task = _get_task(db_session, task.task_id)

    assert task.status == "done"
    assert task.started_at is not None
    assert task.completed_at is not None
    assert task.updated_at is not None


def test_retryable_failure_returns_to_pending_without_completed_timestamp(db_session):
    task = _create_single_task(db_session)

    crud.mark_task_running(db_session, task.task_id)
    crud.mark_task_as_failed_or_retry(
        db_session,
        task.task_id,
        RuntimeError("temporary failure"),
        max_retries=2,
    )
    task = _get_task(db_session, task.task_id)

    assert task.status == "pending"
    assert task.retry_count == 1
    assert task.error_log == "temporary failure"
    assert task.started_at is not None
    assert task.completed_at is None
    assert task.updated_at is not None


def test_terminal_failure_has_completed_timestamp(db_session):
    task = _create_single_task(db_session)

    crud.mark_task_running(db_session, task.task_id)
    crud.mark_task_as_failed_or_retry(
        db_session,
        task.task_id,
        RuntimeError("terminal failure"),
        max_retries=1,
    )
    task = _get_task(db_session, task.task_id)

    assert task.status == "failed"
    assert task.retry_count == 1
    assert task.error_log == "terminal failure"
    assert task.started_at is not None
    assert task.completed_at is not None
    assert task.updated_at is not None
