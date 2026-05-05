from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.models import JobTable
from app.schemas import EvalRequest, JobResponse
from app.database.database import get_db
from app.database import crud


router = APIRouter()


@router.post("/start", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
def create_evaluation_job(request: EvalRequest, db: Session = Depends(get_db)):
    prompts = request.prompts

    try:
        db_job: JobTable = crud.create_eval_job(db=db, prompts=prompts)
        
        return JobResponse(
            job_id=db_job.job_id,
            status=db_job.status,
            total_tasks=len(prompts),
            completed_tasks=0
        )
    
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create evaluation job. Please try again later."
        )
    
    
@router.get("/status/{job_id}", response_model=JobResponse, status_code=status.HTTP_200_OK)
def get_evaluation_job_status_from_id(job_id: int, include_tasks: bool = False, db: Session = Depends(get_db)):
    try:
        db_job: JobTable = crud.find_job_from_id(db=db, job_id=job_id)
    
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database query failed. Please try again later."
        )
    
    if db_job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID {job_id} not found."
        )
    
    total_tasks = crud.get_total_tasks_for_job(db=db, job_id=job_id)
    completed_tasks = crud.get_completed_tasks_for_job(db=db, job_id=job_id)
    finished_tasks = crud.get_finished_tasks_for_job(db=db, job_id=job_id)
    running_tasks = crud.get_running_tasks_for_job(db=db, job_id=job_id)

    if total_tasks == 0: # Edge case, shouldn't happen as we create jobs with at least 1 task, but good to handle just in case
        job_status = "pending"
    elif finished_tasks == total_tasks:
        job_status = "done"
    elif running_tasks > 0 or finished_tasks != completed_tasks:
        job_status = "running" # Some tasks are done/failed, or a worker is currently processing one
    else:
        job_status = "pending" # No tasks have started yet

    return JobResponse(
        job_id=db_job.job_id,
        status=job_status,
        tasks=db_job.tasks if include_tasks else [],
        total_tasks=total_tasks,
        completed_tasks=completed_tasks
    )

    # The response is different from the POST endpoint (len(prompts) vs total_tasks) because the GET endpoint is meant to reflect the current state of the job in the database, which may have changed since the job was created. 
    # The POST endpoint returns the initial number of tasks based on the input prompts, while the GET endpoint calculates the total number of tasks based on what's currently stored in the database for that job ID. 
    # This way, if there were any issues creating tasks or if tasks were added/removed after job creation (not in our current implementation but could be a future feature), the GET endpoint would reflect that accurately.
    # Imagine it was 3 hours after the POST, the prompts list isn't in memory anymore, we must consult the database (slow but accurate)