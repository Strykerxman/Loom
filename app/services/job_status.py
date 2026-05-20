from dataclasses import dataclass
from sqlalchemy.orm import Session

from app.database import crud
from app.schemas import JobStatus


@dataclass(frozen=True)
class JobProgress:
    total_tasks: int
    running_tasks: int
    done_tasks: int
    failed_tasks: int
    terminal_tasks: int
    status: JobStatus


def get_job_progress(db: Session, job_id: int) -> JobProgress:
    """
    
    """
    total_tasks = crud.get_total_tasks_for_job(db=db, job_id=job_id)
    running_tasks = crud.get_running_tasks_for_job(db=db, job_id=job_id)
    done_tasks = crud.get_done_tasks_for_job(db=db, job_id=job_id)
    failed_tasks = crud.get_failed_tasks_for_job(db=db, job_id=job_id)
    terminal_tasks = done_tasks + failed_tasks

    job_status = derive_job_status(
        total_tasks=total_tasks,
        running_tasks=running_tasks,
        terminal_tasks=terminal_tasks,
    )

    return JobProgress(
        total_tasks=total_tasks,
        running_tasks=running_tasks,
        done_tasks=done_tasks,
        failed_tasks=failed_tasks,
        terminal_tasks=terminal_tasks,
        status=job_status
    )


def derive_job_status(
    *,
    total_tasks: int,
    running_tasks: int,
    terminal_tasks: int,
) -> JobStatus:
    """Derive job progress from task counts.

    Job status describes pipeline progress, not whether every task succeeded.
    A job is `done` once every task is terminal. Failed task counts remain
    visible through `failed_tasks` on the API response.
    """
    if total_tasks <= 0:
        return "pending"

    if terminal_tasks >= total_tasks:
        return "done"

    if running_tasks > 0 or terminal_tasks > 0:
        return "running"

    return "pending"
