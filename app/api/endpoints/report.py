from fastapi import APIRouter, status, Depends, HTTPException
from sqlalchemy.orm import Session

from app.services.reports import build_job_leakage_report
from app.services import job_status
from app.database import crud
from app.database.database import get_db
from app.schemas import JobLeakageReport
from app.models import JobTable

router = APIRouter()


@router.get("/report/{job_id}", response_model=JobLeakageReport, status_code=status.HTTP_200_OK)
def get_job_leakage_report(
    job_id: int, 
    db: Session = Depends(get_db)
) -> JobLeakageReport:

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
            detail=f"Could not find job with ID: {job_id}"
        )
    
    progress = job_status.get_job_progress(db, job_id)
    report: JobLeakageReport = build_job_leakage_report(db_job, status=progress.status)

    return report

    