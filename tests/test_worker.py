from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.worker import process_task
from app.services.llm_client import LLMResult, MockLLMClient
import tests.factories as hlp


@dataclass
class FixedResponseLLMClient:
    text: str
    model: str = "fixed-test-llm"
    latency_ms: int = 0

    def complete(self, prompt: str) -> LLMResult:
        return LLMResult(
            text=self.text,
            model=self.model,
            latency_ms=self.latency_ms,
        )


def test_process_task_stores_input_output_pii_evals(db_session: Session):
    task = hlp.create_single_task(db_session, prompt="Please summarize this ticket for jane@example.com")

    llm_client = MockLLMClient(
        failure_rate=0.0,
        min_latency_ms=0,
        max_latency_ms=0,
    )

    process_task(db_session, task, llm_client=llm_client)

    task = hlp.get_task(db_session, task.task_id)

    assert task.status == "done"
    assert task.response["text"]

    evaluation_result = task.evaluation_result

    assert evaluation_result["input_eval"]["has_pii"] is True
    assert evaluation_result["output_eval"]["has_pii"] is True
    assert evaluation_result["output_leaked_pii"] is True


def test_process_task_does_not_mark_different_output_pii_as_leaked(db_session: Session):
    task = hlp.create_single_task(db_session, prompt="Please summarize this ticket for jane@example.com")
    llm_client = FixedResponseLLMClient(text="Contact support@example.com for help.")

    process_task(db_session, task, llm_client=llm_client)

    task = hlp.get_task(db_session, task.task_id)
    evaluation_result = task.evaluation_result

    assert task.status == "done"
    assert task.response["text"] == "Contact support@example.com for help."
    assert evaluation_result["input_eval"]["has_pii"] is True
    assert evaluation_result["output_eval"]["has_pii"] is True
    assert evaluation_result["output_eval"]["matches"]["email"] == ["support@example.com"]
    assert evaluation_result["output_leaked_pii"] is False