from sqlalchemy.orm import Session
from app.models import JobTable, TaskTable


def create_eval_job(db: Session, prompts: list[str]) -> JobTable:
    """
    Creates a Job and its associated Tasks in a single transaction.
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
