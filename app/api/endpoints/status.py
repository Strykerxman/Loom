from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import crud
from app.database.database import get_db
from app.models import JobTable
from app.schemas import JobResponse
from app.services import job_status


router = APIRouter()


@router.get("/status/{job_id}", response_model=JobResponse, status_code=status.HTTP_200_OK)
def get_evaluation_job_status_from_id(
    job_id: int,
    include_tasks: bool = False,
    db: Session = Depends(get_db),
) -> JobResponse:
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

    job_progress: job_status.JobProgress = job_status.get_job_progress(db, job_id)

    return JobResponse(
        job_id=db_job.job_id,
        status=job_progress.status,
        tasks=db_job.tasks if include_tasks else [],
        total_tasks=job_progress.total_tasks,
        finished_tasks=job_progress.terminal_tasks,
        failed_tasks=job_progress.failed_tasks,
    )
