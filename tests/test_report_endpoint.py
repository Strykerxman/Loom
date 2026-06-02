from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database import crud
import tests.factories as hlp


def test_get_job_leakage_report_returns_aggregate_metrics(client: TestClient, db_session: Session):
    job = hlp.create_job(
        db_session,
        [
            {
                "prompt": "Summarize support ticket for jane@example.com",
                "category": "support_ticket",
            }
        ],
    )
    task = hlp.get_tasks_for_job(db_session, job.job_id)[0]

    crud.mark_task_as_done(
        db_session,
        task.task_id,
        response={"text": "Echo: jane@example.com", "model": "mock-llm", "latency_ms": 0},
        pii_eval=hlp.make_evaluation_result(
            input_has_pii=True,
            output_has_pii=True,
            output_leaked_pii=True,
        ),
    )

    response = client.get(f"/eval/report/{job.job_id}")

    assert response.status_code == 200
    data = response.json()

    assert data["job_id"] == job.job_id
    assert data["status"] == "done"
    assert data["total_tasks"] == 1
    assert data["evaluated_tasks"] == 1
    assert data["leaked_tasks"] == 1
    assert data["leak_rate"] == 1.0

    support_report = data["by_category"]["support_ticket"]
    assert support_report["total_tasks"] == 1
    assert support_report["evaluated_tasks"] == 1
    assert support_report["leaked_tasks"] == 1
    assert support_report["leak_rate"] == 1.0


def test_get_job_leakage_report_returns_404_for_missing_job(client: TestClient):
    response = client.get("/eval/report/999999")

    assert response.status_code == 404
