from sqlalchemy.orm import Session

from app.database import crud
import tests.factories as hlp


def test_job_status_moves_to_running_when_task_starts(db_session: Session):
    task = hlp.create_single_task(db_session)

    crud.mark_task_running(db_session, task.task_id)

    job = hlp.get_job(db_session, task.parent_job_id)
    assert job.status == "running"


def test_job_status_moves_to_done_when_all_tasks_are_terminal(db_session: Session):
    task = hlp.create_single_task(db_session)

    crud.mark_task_running(db_session, task.task_id)
    crud.mark_task_as_done(
        db_session,
        task.task_id,
        response={"text": "ok", "model": "mock", "latency_ms": 1},
        pii_eval=hlp.make_evaluation_result(
            input_has_pii=False,
            output_has_pii=False,
            output_leaked_pii=False,
        ),
    )

    job = hlp.get_job(db_session, task.parent_job_id)
    assert job.status == "done"


def test_job_status_returns_to_pending_for_retryable_single_task_failure(db_session: Session):
    task = hlp.create_single_task(db_session)

    crud.mark_task_running(db_session, task.task_id)
    crud.mark_task_as_failed_or_retry(
        db_session,
        task.task_id,
        RuntimeError("temporary failure"),
        max_retries=2,
    )

    job = hlp.get_job(db_session, task.parent_job_id)
    assert job.status == "pending"


def test_job_status_is_done_when_only_remaining_task_fails_terminally(db_session: Session):
    task = hlp.create_single_task(db_session)

    crud.mark_task_running(db_session, task.task_id)
    crud.mark_task_as_failed_or_retry(
        db_session,
        task.task_id,
        RuntimeError("terminal failure"),
        max_retries=1,
    )

    job = hlp.get_job(db_session, task.parent_job_id)
    assert job.status == "done"
