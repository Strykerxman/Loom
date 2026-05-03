from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.models import JobTable
from app.schemas import EvalRequest, JobResponse
from app.database.database import get_db
from app.database.crud import create_eval_job, find_job_from_id


router = APIRouter()


@router.post("/start", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
def create_evaluation_job(request: EvalRequest, db: Session = Depends(get_db)):
    
    prompts = request.prompts

    try:
        db_job: JobTable = create_eval_job(db=db, prompts=prompts)
        return db_job
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create evaluation job: {str(e)}"
        )
    
@router.get("/status/{job_id}", response_model=JobResponse, status_code=status.HTTP_200_OK)
def get_evaluation_job_status_from_id(job_id: int, db: Session = Depends(get_db)):

    try:
        db_job: JobTable = find_job_from_id(db=db, job_id=job_id)
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database query failed: {str(e)}"
        )
    
    if db_job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID {job_id} not found."
        )
    
    return db_job