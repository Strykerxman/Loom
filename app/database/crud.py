from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import JobTable, TaskTable
from app.services.job_status import derive_job_status


TaskPayloadInput = str | dict[str, Any]


def create_eval_job(db: Session, prompts: list[TaskPayloadInput]) -> JobTable:
    """
    Creates a Job and its associated Tasks in a single transaction.

    A Job is created with the "pending" status. Its created Tasks have the "pending" status.
    Prompts may be plain strings or structured task payloads containing prompt metadata.
    """

    db_job = JobTable(status="pending")

    tasks = [
        TaskTable(
            payload=_normalise_task_payload(prompt),
            status="pending",
        )
        for prompt in prompts
    ]

    db_job.tasks = tasks

    db.add(db_job)
    db.commit()
    db.refresh(db_job)

    return db_job


def _normalise_task_payload(prompt: TaskPayloadInput) -> dict[str, Any]:
    if isinstance(prompt, str):
        return {"prompt": prompt}

    if "prompt" not in prompt or not isinstance(prompt["prompt"], str):
        raise ValueError("Task payload must contain a string 'prompt'")

    return dict(prompt)


def find_job_from_id(db: Session, job_id: int) -> JobTable | None:
    return (
        db.query(JobTable)
        .filter(JobTable.job_id == job_id)
        .first()
    )


def find_pending_task(db: Session) -> TaskTable | None:
    return (
        db.query(TaskTable)
        .filter(TaskTable.status == "pending")
        .with_for_update(skip_locked=True)
        .first()
    )


def mark_task_running(db: Session, task_id: int) -> None:
    task = db.query(TaskTable).filter(TaskTable.task_id == task_id).first()

    if task is None:
        return

    task.status = "running"
    task.started_at = func.now()
    task.updated_at = func.now()

    refresh_job_status(db, task.parent_job_id)
    db.commit()


def mark_task_as_done(db: Session, task_id: int, response: dict, pii_eval: dict) -> None:
    task = db.query(TaskTable).filter(TaskTable.task_id == task_id).first()

    if task is None:
        return

    task.status = "done"
    task.completed_at = func.now()
    task.updated_at = func.now()
    task.response = response
    task.evaluation_result = pii_eval

    refresh_job_status(db, task.parent_job_id)
    db.commit()


def mark_task_as_failed_or_retry(db: Session, task_id: int, error, max_retries: int = 3) -> None:
    task = db.query(TaskTable).filter(TaskTable.task_id == task_id).first()

    if task is None:
        return

    new_retry_count = (task.retry_count or 0) + 1
    is_failed = new_retry_count >= max_retries

    task.retry_count = new_retry_count
    task.error_log = str(error)
    task.status = "failed" if is_failed else "pending"
    task.updated_at = func.now()

    if is_failed:
        task.completed_at = func.now()

    refresh_job_status(db, task.parent_job_id)
    db.commit()


def refresh_job_status(db: Session, job_id: int) -> None:
    """Persist the aggregate job status implied by the current task states.

    API responses still derive progress from task counts, but keeping jobs.status in
    sync prevents the database row from telling a stale story when inspected directly.
    """
    db.flush()

    total_tasks = get_total_tasks_for_job(db, job_id)
    running_tasks = get_running_tasks_for_job(db, job_id)
    terminal_tasks = get_terminal_tasks_for_job(db, job_id)

    db.query(JobTable).filter(JobTable.job_id == job_id).update({
        JobTable.status: derive_job_status(
            total_tasks=total_tasks,
            running_tasks=running_tasks,
            terminal_tasks=terminal_tasks,
        )
    })


def get_total_tasks_for_job(db: Session, job_id: int) -> int:
    return db.query(func.count(TaskTable.task_id)).filter(TaskTable.parent_job_id == job_id).scalar()


def get_done_tasks_for_job(db: Session, job_id: int) -> int:
    return db.query(func.count(TaskTable.task_id)).filter(
        TaskTable.parent_job_id == job_id,
        TaskTable.status == "done",
    ).scalar()


def get_terminal_tasks_for_job(db: Session, job_id: int) -> int:
    return db.query(func.count(TaskTable.task_id)).filter(
        TaskTable.parent_job_id == job_id,
        TaskTable.status.in_(["done", "failed"]),
    ).scalar()


def get_finished_tasks_for_job(db: Session, job_id: int) -> int:
    # Backwards-compatible name. "Finished" means terminal: done or failed.
    return get_terminal_tasks_for_job(db=db, job_id=job_id)


def get_running_tasks_for_job(db: Session, job_id: int) -> int:
    return db.query(func.count(TaskTable.task_id)).filter(
        TaskTable.parent_job_id == job_id,
        TaskTable.status == "running",
    ).scalar()


def get_failed_tasks_for_job(db: Session, job_id: int) -> int:
    return db.query(func.count(TaskTable.task_id)).filter(
        TaskTable.parent_job_id == job_id,
        TaskTable.status == "failed",
    ).scalar()
