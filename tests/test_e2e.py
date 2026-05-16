import requests
import time
import sys
import os

import pytest

from app.config import load_env
from scripts.worker_utils import spawn_workers, stop_workers

# Pytest path: `pytest --run-e2e tests/test_e2e.py -s` starts DB + Uvicorn automatically.
# Manual path: start DB + Uvicorn yourself, then run `python tests/test_e2e.py`.
os.environ.setdefault("ENV_FILE", ".env.test")
load_env(override=True)

BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8001")
AUTOSPAWN_WORKERS = 3


def run_e2e_test(base_url: str = BASE_URL):
    print("🚀 Starting Loom E2E Test...")

    # 1. Create a new job with test prompts (some with PII, some clean)
    payload = {
        "prompts": [
            "Hello, my email is test1@example.com",
            "This is a clean prompt.",
            "Contact me at admin@corp.com and ceo@corp.com"
        ]
    }

    workers = []
    
    print("\n📦 POST /eval/start")
    try:
        response = requests.post(f"{base_url}/eval/start", json=payload, timeout=5)
        response.raise_for_status()

        job_data = response.json()
        job_id = job_data["job_id"]

        print(f"✅ Job created successfully! Job ID: {job_id}")
        print(f"   Status: {job_data['status']}, Tasks: {job_data['total_tasks']}")

        # capture worker logs into files to avoid interleaving with test console output
        workers = spawn_workers(AUTOSPAWN_WORKERS, capture_logs=True, stream_to_console=False)

        # 2. Poll the status endpoint until the job is done
        print("\n⏳ Polling GET /eval/status/{job_id} for completion...")
        max_attempts = 30
        attempts = 0
        
        while attempts < max_attempts:

            response = requests.get(f"{base_url}/eval/status/{job_id}?include_tasks=false", timeout=5) # false to improve performance
            response.raise_for_status()

            data = response.json()
            
            status = data["status"]
            total = data["total_tasks"]
            finished = data["finished_tasks"]
            failed = data["failed_tasks"]
            
            print(f"\r   [{attempts+1}/{max_attempts}] Status: {status} | Progress: {finished}/{total}", end="\r", flush=True)
            
            if finished == total or status == "done":
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
        response = requests.get(f"{base_url}/eval/status/{job_id}?include_tasks=true", timeout=5) # one check with true to 
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
            input_eval = eval_result.get("input_eval") or {}
            output_eval = eval_result.get("output_eval") or {}

            if status == "done":
                print(f"   - Input PII Found: {input_eval.get('has_pii')}")
                print(f"   - Output PII Found: {output_eval.get('has_pii')}")
                print(f"   - Output Leaked PII: {eval_result.get('output_leaked_pii')}")
                
                if input_eval.get('matches'):
                    print(f"   - Input PII Matches: {input_eval.get('matches')}")
                if output_eval.get('matches'):
                    print(f"   - Output PII Matches: {output_eval.get('matches')}")

            elif status == "failed":
                print(f"   - Failed with error: {task.get('error_log')}")
            else:
                print("   - Not terminal (unexpected in final fetch)")
            print("   ---")

        total = data["total_tasks"]
        finished = data["finished_tasks"]
        failed = data["failed_tasks"]
        assert 0 <= failed <= finished <= total
    
    except requests.exceptions.RequestException as e:
        print(f"❌ ERROR: FastAPI request failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ ERROR: E2E test failed: {e}")
        sys.exit(1)

    finally:
        if workers:
            stop_workers(workers)
            print("\nWorker logs:")
            for worker in workers:
                if worker.log_path is not None:
                    print(f" - {worker.log_path}")

    print("\n🎉 E2E Test Complete!")


@pytest.mark.e2e
def test_e2e_pipeline(uvicorn_server):
    run_e2e_test(uvicorn_server)


if __name__ == "__main__":
    run_e2e_test()
