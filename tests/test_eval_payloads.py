from sqlalchemy.orm import Session

from app.database import crud
from app.models import TaskTable
from app.schemas import EvalPrompt, EvalRequest


def _only_task_for_job(db_session: Session, job_id: int) -> TaskTable:
    return db_session.query(TaskTable).filter(TaskTable.parent_job_id == job_id).one()


def test_eval_request_accepts_plain_and_structured_prompts():
    request = EvalRequest.model_validate(
        {
            "prompts": [
                "plain prompt",
                {
                    "prompt": "structured prompt with jane@example.com",
                    "category": "support_ticket",
                    "expected_pii_types": ["email"],
                },
            ]
        }
    )

    assert request.prompts[0] == "plain prompt"
    assert isinstance(request.prompts[1], EvalPrompt)
    assert request.prompts[1].category == "support_ticket"
    assert request.prompts[1].expected_pii_types == ["email"]


def test_create_eval_job_preserves_plain_prompt_payload(db_session: Session):
    job = crud.create_eval_job(db_session, ["plain prompt"])

    task = _only_task_for_job(db_session, job.job_id)

    assert task.payload == {"prompt": "plain prompt"}


def test_create_eval_job_preserves_structured_prompt_metadata(db_session: Session):
    job = crud.create_eval_job(
        db_session,
        [
            {
                "prompt": "Summarize this ticket for jane@example.com",
                "category": "support_ticket",
                "expected_pii_types": ["email"],
            }
        ],
    )

    task = _only_task_for_job(db_session, job.job_id)

    assert task.payload["prompt"] == "Summarize this ticket for jane@example.com"
    assert task.payload["category"] == "support_ticket"
    assert task.payload["expected_pii_types"] == ["email"]
