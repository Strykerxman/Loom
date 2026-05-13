import requests
import time
import sys
from scripts.worker_utils import spawn_workers, stop_workers
# Run this test by instantiating a worker (see README.md) and make sure a server is running (db + fastapi).
# Then go into another command line and run `python tests/test_e2e.py` from the Loom directory (/path/to/Loom)

BASE_URL = "http://127.0.0.1:8000"
AUTOSPAWN_WORKERS = 3

def run_e2e_test():
    print("🚀 Starting Loom E2E Test...")

    # 1. Create a new job with test prompts (some with PII, some clean)
    payload = {
        "prompts": [
            "Hello, my email is test1@example.com",
            "This is a clean prompt.",
            "Contact me at admin@corp.com and ceo@corp.com"
        ]
    }
    
    print("\n📦 POST /eval/start")
    try:
        # capture worker logs into files to avoid interleaving with test console output
        workers = spawn_workers(AUTOSPAWN_WORKERS, capture_logs=True, stream_to_console=False)
        
        response = requests.post(f"{BASE_URL}/eval/start", json=payload)
        response.raise_for_status()

        job_data = response.json()
        job_id = job_data["job_id"]

        print(f"✅ Job created successfully! Job ID: {job_id}")
        print(f"   Status: {job_data['status']}, Tasks: {job_data['total_tasks']}")

    except requests.exceptions.ConnectionError:
        print("❌ ERROR: Could not connect to FastAPI. Is uvicorn running?")
        sys.exit(1)
    except Exception as e:
        print(f"❌ ERROR: Failed to create job: {e}")
        sys.exit(1)

    # 2. Poll the status endpoint until the job is done
    print("\n⏳ Polling GET /eval/status/{job_id} for completion...")
    max_attempts = 30
    attempts = 0
    
    while attempts < max_attempts:

        response = requests.get(f"{BASE_URL}/eval/status/{job_id}?include_tasks=false") # false to improve performance
        response.raise_for_status()

        data = response.json()
        
        status = data["status"]
        total = data["total_tasks"]
        finished = data["finished_tasks"]
        failed = data["failed_tasks"]
        
        print(f"\r   [{attempts+1}/{max_attempts}] Status: {status} | Progress: {finished}/{total}", end="\r", flush=True)
        
        if finished == total or status in ["done", "failed"]:
            sys.stdout.write("\033[K")
            print(f"\r   ✅ Job finished processing! Failed: {failed}/{total}")
            break
        time.sleep(2)
        attempts += 1
        
    if attempts == max_attempts:
        print("\n⚠️ WARNING: Polling timed out. Are your workers running? (`python -m app.worker`)")
        sys.exit(1)

    # 3. Validate the actual PII results
    print("\n🔍 Validating Task Results...")
    response = requests.get(f"{BASE_URL}/eval/status/{job_id}?include_tasks=true") # one check with true to 
    response.raise_for_status()

    data = response.json()
    tasks = data.get("tasks", [])
    
    if not tasks:
        print("❌ ERROR: No tasks returned even though include_tasks=true was set!")
        sys.exit(1)
        
    for task in tasks:
       status = task["status"]
       print(f"   Task ID: {task['task_id']} | Status: {status}")
       print(f"   - Prompt: {task['payload'].get('prompt')}")

       eval_result = task.get("evaluation_result") or {}

       if status == "done":
           print(f"   - PII Found: {eval_result.get('has_pii')}")
           if eval_result.get("has_pii"):
               print(f"   - PII Matches: {eval_result.get('matches')}")
       elif status == "failed":
           print(f"   - Failed with error: {task.get('error_log')}")
       else:
           print("   - Not terminal (unexpected in final fetch)")
       print("   ---")

    total = data["total_tasks"]
    finished = data["finished_tasks"]
    failed = data["failed_tasks"]
    assert 0 <= failed <= finished <= total

    if 'workers' in locals() and workers:
        stop_workers(workers)

    # Optionally print where logs were written
    if 'workers' in locals() and workers:
        print("\nWorker logs:")
        for worker in workers:
            if worker.log_path is not None:
                print(f" - {worker.log_path}")

    print("\n🎉 E2E Test Complete!")

if __name__ == "__main__":
    run_e2e_test()