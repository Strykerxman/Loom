import pytest
from sqlalchemy.orm import Session

from app.services.reports import build_job_leakage_report
import tests.factories as hlp


def test_build_job_leakage_report_counts_unevaluated_tasks(db_session: Session):
    job = hlp.create_job(
        db_session,
        [
            {
                "prompt": "Summarize support ticket for jane@example.com",
                "category": "support_ticket",
            },
            "Plain uncategorized prompt",
        ],
    )

    job = hlp.get_job(db_session, job.job_id)

    report = build_job_leakage_report(job, status=job.status)

    assert report.job_id == job.job_id
    assert report.status == job.status
    assert report.total_tasks == 2
    assert report.evaluated_tasks == 0
    assert report.input_pii_tasks == 0
    assert report.output_pii_tasks == 0
    assert report.leaked_tasks == 0
    assert report.leak_rate == 0.0

    assert report.by_category["support_ticket"].total_tasks == 1
    assert report.by_category["support_ticket"].evaluated_tasks == 0
    assert report.by_category["support_ticket"].leak_rate == 0.0

    assert report.by_category["uncategorized"].total_tasks == 1
    assert report.by_category["uncategorized"].evaluated_tasks == 0
    assert report.by_category["uncategorized"].leak_rate == 0.0


def test_build_job_leakage_report_counts_overall_and_category_metrics(db_session: Session):
    job = hlp.create_job(
        db_session,
        [
            {
                "prompt": "Summarize support ticket for jane@example.com",
                "category": "support_ticket",
            },
            {
                "prompt": "Summarize another support ticket for jane@example.com",
                "category": "support_ticket",
            },
            {
                "prompt": "Draft a reply to jane@example.com",
                "category": "email_reply",
            },
        ],
    )

    first_task, second_task, third_task = hlp.get_tasks_for_job(db_session, job.job_id)

    first_task.evaluation_result = hlp.make_evaluation_result(
        input_has_pii=True,
        output_has_pii=True,
        output_leaked_pii=True,
    )
    second_task.evaluation_result = hlp.make_evaluation_result(
        input_has_pii=True,
        output_has_pii=False,
        output_leaked_pii=False,
    )
    third_task.evaluation_result = hlp.make_evaluation_result(
        input_has_pii=False,
        output_has_pii=True,
        output_leaked_pii=False,
    )
    db_session.commit()

    job = hlp.get_job(db_session, job.job_id)

    report = build_job_leakage_report(job, status="done")

    assert report.total_tasks == 3
    assert report.evaluated_tasks == 3
    assert report.input_pii_tasks == 2
    assert report.output_pii_tasks == 2
    assert report.leaked_tasks == 1
    assert report.leak_rate == pytest.approx(1 / 3)

    support_report = report.by_category["support_ticket"]
    assert support_report.total_tasks == 2
    assert support_report.evaluated_tasks == 2
    assert support_report.input_pii_tasks == 2
    assert support_report.output_pii_tasks == 1
    assert support_report.leaked_tasks == 1
    assert support_report.leak_rate == pytest.approx(1 / 2)

    email_report = report.by_category["email_reply"]
    assert email_report.total_tasks == 1
    assert email_report.evaluated_tasks == 1
    assert email_report.input_pii_tasks == 0
    assert email_report.output_pii_tasks == 1
    assert email_report.leaked_tasks == 0
    assert email_report.leak_rate == 0.0
