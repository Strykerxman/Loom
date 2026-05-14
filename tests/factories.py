from sqlalchemy.orm import Session

from app.database import crud
from app.models import TaskTable


def get_task(db_session: Session, task_id: int) -> TaskTable:
    db_session.expire_all()
    return db_session.query(TaskTable).filter(TaskTable.task_id == task_id).one()


def create_single_task(db_session: Session, prompt: str = "hello") -> TaskTable:
    job = crud.create_eval_job(db_session, [prompt])
    return db_session.query(TaskTable).filter(TaskTable.parent_job_id == job.job_id).one()
    