from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import crud
from app.database.database import get_db
from app.models import JobTable
from app.schemas import EvalRequest, JobResponse


router = APIRouter()


@router.post("/start", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
def create_evaluation_job(request: EvalRequest, db: Session = Depends(get_db)):
    prompts = request.prompts

    try:
        db_job: JobTable = crud.create_eval_job(db=db, prompts=prompts)

        return JobResponse(
            job_id=db_job.job_id,
            status="pending",
            total_tasks=len(prompts),
            finished_tasks=0,
            failed_tasks=0,
        )

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create evaluation job. Please try again later.",
        )