from sqlalchemy.orm import Session

from app.worker import process_task
from app.services.llm_client import MockLLMClient
import tests.factories as hlp


def test_process_task_stores_input_output_pii_evals(db_session: Session):
    task = hlp.create_single_task(db_session, prompt="Please summarize this ticket for jane@example.com")

    llm_client = MockLLMClient(
        failure_rate=0.0,
        min_latency_ms=0.0,
        max_latency_ms=0.0,
    )

    process_task(db_session, task, llm_client=llm_client)

    task = hlp.get_task(db_session, task.task_id)

    assert task.status == "done"
    assert task.response["text"]

    evaluation_result = task.evaluation_result

    assert evaluation_result["input_eval"]["has_pii"] is True
    assert evaluation_result["output_eval"]["has_pii"] is True
    assert evaluation_result["output_leaked_pii"] is True