import random
import time
from .database.database import SessionLocal
from .database.crud import find_pending_task
from .services.evaluator import evaluate_pii
from .schemas.schemas import PIIEval


def run_worker(): 
    print("Worker started. Listening for tasks...")

    while True:
        with SessionLocal() as db:
            try:
                task = find_pending_task(db=db)

                if not task:
                    time.sleep(1)
                    continue

                print(f"\nWorker picked up Task ID: {task.task_id}")

                try: 
                    task.status = "running"
                    db.commit() # Performs an UPDATE to the database, no new ID to fetch or anything, claim transaction

                    prompt = task.payload["prompt"]

                    time.sleep(random.randint(2, 5)) # Simulate variable LLM processing time
                    if random.random() < 0.3: # 30% chance of failure to test retry mechanism
                        print(f"    An error has occurred while calling the LLM.")
                        raise ValueError("Simulated task failure")
                    
                    mock_response = f"Echo: {prompt}"
                    pii_eval: PIIEval = evaluate_pii(text=mock_response)
                    task.response = {"text": mock_response, "model": "mock-llm"}
                    task.evaluation_result = pii_eval.model_dump()
                    task.error_log = None
                    task.status = "done" # Update the task status to "done" in the database, no error was raised, so we consider the task successfully completed
                    print(f"    ✅ Task ID {task.task_id} done! ")

                except Exception as e:
                    task.retry_count += 1
                    task.error_log = str(e)

                    if task.retry_count >= 3:
                        task.status = "failed"
                        print(f"    ❌ Task ID {task.task_id} failed permanently ({task.retry_count}/3)")

                    else:
                        task.status = "pending"
                        print(f"    ⚠️ Task ID {task.task_id} retry scheduled ({task.retry_count}/3)")
                
                db.commit() # Finalize transaction, update its status to either done if success, pending if to be tried again and failed if max retries 
                print(f"    Updating task status={task.status}.")

            except Exception as db_e:
                print(f"Database session error. Check connections or try again later.")
                db.rollback()
                time.sleep(5)


if __name__ == "__main__":
    run_worker()