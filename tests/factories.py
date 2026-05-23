from typing import Any

from sqlalchemy.orm import Session

from app.database import crud
from app.models import JobTable, TaskTable
from app.pii import PIIEval, TaskEvaluationResult


def get_task(db_session: Session, task_id: int) -> TaskTable:
    db_session.expire_all()
    return db_session.query(TaskTable).filter(TaskTable.task_id == task_id).one()


def create_single_task(db_session: Session, prompt: str = "hello") -> TaskTable:
    job = crud.create_eval_job(db_session, [prompt])
    return db_session.query(TaskTable).filter(TaskTable.parent_job_id == job.job_id).one()


def create_job(db_session: Session, prompts: list[str | dict[str, Any]]) -> JobTable:
    return crud.create_eval_job(db_session, prompts)


def get_job(db_session: Session, job_id: int) -> JobTable:
    db_session.expire_all()
    job = crud.find_job_from_id(db_session, job_id)
    assert job is not None
    return job


def get_tasks_for_job(db_session: Session, job_id: int) -> list[TaskTable]:
    return (
        db_session.query(TaskTable)
        .filter(TaskTable.parent_job_id == job_id)
        .order_by(TaskTable.task_id)
        .all()
    )


def make_pii_eval(*, has_pii: bool, value: str = "jane@example.com") -> PIIEval:
    if not has_pii:
        return PIIEval(
            has_pii=False,
            risk_score=0.0,
        )

    return PIIEval(
        has_pii=True,
        types=["email"],
        matches={"email": [value]},
        risk_score=1.0,
    )


def make_evaluation_result(
    *,
    input_has_pii: bool,
    output_has_pii: bool,
    output_leaked_pii: bool,
) -> dict[str, Any]:
    return TaskEvaluationResult(
        input_eval=make_pii_eval(has_pii=input_has_pii),
        output_eval=make_pii_eval(has_pii=output_has_pii),
        output_leaked_pii=output_leaked_pii,
    ).model_dump()
