import time
from .database.database import SessionLocal
from .database.crud import find_pending_task

db = SessionLocal()

def run_worker(): 
    print("Worker started. Listening for tasks...")

    while True:
        task = find_pending_task(db=db)

        if task:
            print(f"Picked up Task ID: {task.task_id}")
            task.status = "running"
            db.commit() # Performs an UPDATE to the database, no new ID to fetch or anything

            time.sleep(2)

            task.status = "done"
            db.commit()
            print(f"Finished Task ID {task.task_id}")

        else:
            time.sleep(1)

if __name__ == "__main__":
    run_worker()