import random
import time
from .database.database import SessionLocal
from .database.crud import find_pending_task
from .services.evaluator import evaluate_pii
from .schemas.schemas import PIIEval

db = SessionLocal()

def run_worker(): 
    print("Worker started. Listening for tasks...")

    while True:
        task = find_pending_task(db=db)

        if task:
            print(f"Picked up Task ID: {task.task_id}")
            task.status = "running"
            db.commit() # Performs an UPDATE to the database, no new ID to fetch or anything

            try:
                prompt = task.payload["prompt"]

                time.sleep(random.randint(2, 5)) # Simulate variable LLM processing time
                if random.random() < 0.3: # 30% chance of failure to test retry mechanism
                    raise ValueError("Simulated task failure")
                
                mock_response = f"Echo: {prompt}"
                pii_eval: PIIEval = evaluate_pii(text=mock_response)
                task.response = {"text": mock_response, "model": "mock-llm"}
                task.evaluation_result = pii_eval.model_dump()
                task.error_log = None
                task.status = "done" # Update the task status to "done" in the database, no error was raised, so we consider the task successfully completed

            except Exception as e:
                task.retry_count += 1
                task.error_log = str(e)

                if task.retry_count >= 3:
                    task.status = "failed"
                    print(f"Task ID {task.task_id} failed after 3 retries.")

                else:
                    task.status = "pending"
                    print(f"Task ID {task.task_id} failed. Retrying ({task.retry_count}/3)...")


            db.commit()
            print(f"Finished processing Task ID {task.task_id}. Status: {task.status}")

        else:
            time.sleep(1)
        

if __name__ == "__main__":
    run_worker()