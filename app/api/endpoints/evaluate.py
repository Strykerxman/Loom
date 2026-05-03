from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.models import JobTable
from app.schemas import EvalRequest, JobResponse
from app.database.database import get_db
from app.database.crud import create_eval_job


router = APIRouter()


@router.post("/eval", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
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
    