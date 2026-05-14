from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import crud
from app.database.database import get_db
from app.models import JobTable
from app.schemas import JobResponse
from app.services.job_status import derive_job_status


router = APIRouter()


@router.get("/status/{job_id}", response_model=JobResponse, status_code=status.HTTP_200_OK)
def get_evaluation_job_status_from_id(
    job_id: int,
    include_tasks: bool = False,
    db: Session = Depends(get_db),
):
    try:
        db_job: JobTable | None = crud.find_job_from_id(db=db, job_id=job_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database query failed. Please try again later.",
        )

    if db_job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID {job_id} not found.",
        )

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

    return JobResponse(
        job_id=db_job.job_id,
        status=job_status,
        tasks=db_job.tasks if include_tasks else [],
        total_tasks=total_tasks,
        finished_tasks=terminal_tasks,
        failed_tasks=failed_tasks,
    )
