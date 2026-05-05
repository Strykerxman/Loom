import requests
import time
import sys

BASE_URL = "http://127.0.0.1:8000"

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
    max_attempts = 15
    attempts = 0
    
    while attempts < max_attempts:
        resp = requests.get(f"{BASE_URL}/eval/status/{job_id}?include_tasks=true")
        data = resp.json()
        
        status = data["status"]
        completed = data["completed_tasks"]
        total = data["total_tasks"]
        
        print(f"   [{attempts+1}/{max_attempts}] Status: {status} | Progress: {completed}/{total}")
        
        if status in ["done", "failed"]:
            print("\n✅ Job finished processing!")
            break
        time.sleep(2)
        attempts += 1
        
    if attempts == max_attempts:
        print("\n⚠️ WARNING: Polling timed out. Are your workers running? (`python -m app.worker`)")
        sys.exit(1)

    # 3. Validate the actual PII results
    print("\n🔍 Validating Task Results...")
    tasks = data.get("tasks", [])
    
    if not tasks:
        print("❌ ERROR: No tasks returned even though include_tasks=true was set!")
        sys.exit(1)
        
    for task in tasks:
        print(f"   Task ID: {task['task_id']}")
        print(f"   - Prompt: {task['payload'].get('prompt')}")
        eval_result = task.get("evaluation_result", {})
        print(f"   - PII Found: {eval_result.get('has_pii')}")
        if eval_result.get("has_pii"):
            print(f"   - PII Matches: {eval_result.get('matches')}")
        print("   ---")

    print("\n🎉 E2E Test Complete!")

if __name__ == "__main__":
    run_e2e_test()