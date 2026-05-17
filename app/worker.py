import time
from sqlalchemy.orm import Session
from collections.abc import Callable

from .database import crud
from .database.database import get_session_factory
from .services.evaluator import evaluate_pii
from .schemas import TaskEvaluationResult
from .models.models import TaskTable
from .services.llm_client import create_llm_client, LLMClient


WORKER_IDLE_TIMEOUT = 60 * 10 # 10 minutes
WORKER_SLEEP_INTERVAL = 1 # 1 second, short so we can make sure we pick up tasks quickly, but not too short to avoid hammering the database when idle
DB_BACKOFF_INTERVAL = 5
MAX_RETRIES = 3


def run_worker(sessionfactory: Callable[[], Session], llm_client: LLMClient | None = None):
    idle_since: float | None = None
    llm_client = llm_client or create_llm_client()

    print("Worker started. Listening for tasks...")

    while True:
        sleep_for: int | None = None

        try:
            with sessionfactory() as db:
                task = crud.find_pending_task(db=db)

                if task is not None:
                    print(f"Picked up task {task.task_id} from job #{task.parent_job_id}", flush=True)
                    idle_since = None
                    process_task(db, task, llm_client)

                else:
                    if idle_since is None:
                        idle_since = time.monotonic()
                    
                    elif (time.monotonic() - idle_since >= WORKER_IDLE_TIMEOUT):
                        print("\nWorker has been idle for too long, shutting down.")
                        return

                    sleep_for = WORKER_SLEEP_INTERVAL

        except Exception as db_e:
            print(f"Database session error. Check connections or try again later: {str(db_e)}")
            sleep_for = DB_BACKOFF_INTERVAL
            
        if sleep_for is not None:
            time.sleep(sleep_for)
            sleep_for = None


def process_task(db: Session, task: TaskTable, llm_client: LLMClient) -> None:
    """Processing logic for handling a single task."""

    task_id = task.task_id
    prompt = get_prompt(task)

    crud.mark_task_running(db, task_id)
    print(f"Processing task {task_id}", flush=True)

    try:
        input_eval = evaluate_pii(prompt)
        result = llm_client.complete(prompt)
        output_eval = evaluate_pii(result.text)

        evaluation_result = TaskEvaluationResult(
            input_eval=input_eval,
            output_eval=output_eval,
            output_leaked_pii=output_eval.has_pii
        )

        response_payload = { # construct a response payload
            "text": result.text,
            "model": result.model,
            "latency_ms": result.latency_ms
        }

        crud.mark_task_as_done(db, task_id, response_payload, evaluation_result.model_dump())
        print(f"Completed task {task_id}", flush=True)

    except Exception as e:
        db.rollback()
        crud.mark_task_as_failed_or_retry(db, task_id, e, MAX_RETRIES)
        print(f"Task {task_id} failed: {e}", flush=True)


def get_prompt(task: TaskTable) -> str:
    """Extracts the prompt from the task payload. Can be extended to support more complex logic."""
    prompt = task.payload.get("prompt")

    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError(f"Task {task.task_id} has invalid or missing 'prompt' in payload")

    return prompt

if __name__ == "__main__":
    run_worker(get_session_factory())