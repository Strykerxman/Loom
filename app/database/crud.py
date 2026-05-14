from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import JobTable, TaskTable


def create_eval_job(db: Session, prompts: list[str]) -> JobTable:
    """
    Creates a Job and its associated Tasks in a single transaction.

    A Job is created with the "pending" status. Its created Tasks have the "pending" status.
    """

    db_job = JobTable(status = "pending")

    tasks = [
        TaskTable(
            payload={"prompt": prompt},
            status="pending"
        )
        for prompt in prompts
    ]

    db_job.tasks = tasks

    db.add(db_job) 
    db.commit()
    db.refresh(db_job) # Update Python memory object (db_job) with fresh data, so it knows its own ID
    # Runs a SELECT, grabs the newly inserted row and updates db_job with new data, like job_id *(corresponding to row number for now)*
    # Needed as the API response will have the created job ID and it can't access it once the Session is closed (after the database commit if no refresh)
     
    return db_job


def find_job_from_id(db: Session, job_id: int) -> JobTable:
    return (
        db.query(JobTable)
        .filter(JobTable.job_id == job_id)
        .first()
    )


def find_pending_task(db: Session) -> TaskTable:
    return (
        db.query(TaskTable)
        .filter(TaskTable.status == "pending")
        .with_for_update(skip_locked=True) # Ensures that if multiple workers query for pending tasks at the same time, they won't pick the same one
        .first()
    )


def mark_task_running(db: Session, task_id: int) -> None:
    db.query(TaskTable).filter(TaskTable.task_id == task_id).update({
            TaskTable.status: "running",
            TaskTable.started_at: func.now(),
            TaskTable.updated_at: func.now()
    })
    db.commit()


def mark_task_as_done(db: Session, task_id: int, response: dict, pii_eval: dict) -> None:
    db.query(TaskTable).filter(TaskTable.task_id == task_id).update({
        TaskTable.status: "done",
        TaskTable.completed_at: func.now(),
        TaskTable.updated_at: func.now(),
        TaskTable.response: response,
        TaskTable.evaluation_result: pii_eval
    })
    db.commit()


def mark_task_as_failed_or_retry(db: Session, task_id: int, error, max_retries: int = 3) -> None:
    task = db.query(TaskTable).filter(TaskTable.task_id == task_id).first()

    if task is None:
        return
    
    new_retry_count = (task.retry_count or 0) + 1
    is_failed = new_retry_count >= max_retries

    db.query(TaskTable).filter(TaskTable.task_id == task_id).update({
        TaskTable.retry_count: new_retry_count,
        TaskTable.error_log: str(error),
        TaskTable.status: "failed" if is_failed else "pending",
        TaskTable.updated_at: func.now(),
        TaskTable.completed_at: func.now() if is_failed else TaskTable.completed_at
    })

    db.commit()
    

def get_total_tasks_for_job(db: Session, job_id: int) -> int:
    return db.query(func.count(TaskTable.task_id)).filter(TaskTable.parent_job_id == job_id).scalar()


def get_done_tasks_for_job(db: Session, job_id: int) -> int:
    return db.query(func.count(TaskTable.task_id)).filter(
        TaskTable.parent_job_id == job_id,
        TaskTable.status == "done"
    ).scalar()


def get_terminal_tasks_for_job(db: Session, job_id: int) -> int:
    return db.query(func.count(TaskTable.task_id)).filter(
        TaskTable.parent_job_id == job_id,
        TaskTable.status.in_(["done", "failed"])
    ).scalar()


def get_finished_tasks_for_job(db: Session, job_id: int) -> int:
    # Backwards-compatible name. "Finished" means terminal: done or failed.
    return get_terminal_tasks_for_job(db=db, job_id=job_id)


def get_running_tasks_for_job(db: Session, job_id: int) -> int:
    return db.query(func.count(TaskTable.task_id)).filter(
        TaskTable.parent_job_id == job_id, 
        TaskTable.status == "running"
    ).scalar()


def get_failed_tasks_for_job(db: Session, job_id: int) -> int:
    return db.query(func.count(TaskTable.task_id)).filter(
        TaskTable.parent_job_id == job_id, 
        TaskTable.status == "failed"
    ).scalar()