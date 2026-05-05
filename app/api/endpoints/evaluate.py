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
        
        return JobResponse(
            job_id=db_job.job_id,
            status=db_job.status,
            total_tasks=len(db_job.tasks),
            completed_tasks=0
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create evaluation job. Please try again later."
        )
    
    
@router.get("/status/{job_id}", response_model=JobResponse, status_code=status.HTTP_200_OK)
def get_evaluation_job_status_from_id(job_id: int, db: Session = Depends(get_db)):
    try:
        db_job: JobTable = find_job_from_id(db=db, job_id=job_id)
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database query failed. Please try again later."
        )
    
    if db_job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID {job_id} not found."
        )
    
    total_tasks = len(db_job.tasks)
    terminal_statuses = {"failed", "done"}
    completed_tasks = len([t for t in db_job.tasks if t.status == "done"])
    finished_tasks = len([t for t in db_job.tasks if t.status in terminal_statuses])

    if total_tasks == 0: # edge case, shouldn't happen as we create jobs with at least 1 task, but good to handle just in case
        job_status = "pending"
    elif finished_tasks == total_tasks:
        job_status = "done"
    elif finished_tasks > 0 or any(t.status == "running" for t in db_job.tasks):
        job_status = "running" # some tasks are done/failed, or a worker is currently processing one
    else:
        job_status = "pending" # no tasks have started yet

    return JobResponse(
        job_id=db_job.job_id,
        status=job_status,
        total_tasks=total_tasks,
        completed_tasks=completed_tasks
    )
    