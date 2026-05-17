import os

import requests
from pydantic import ValidationError

from app.services.redteam_prompts import generate_redteam_prompts, RedTeamPrompt
from app.schemas import JobResponse
# Purpose:
# Submit Loom's generated red-team prompt suite to a running FastAPI server.

# Preconditions:
# - Docker/Postgres is running.
# - Uvicorn server is running.
# - At least one worker is running.
# - The worker has access to the same environment variables as the API.
# - If using Groq, GROQ credentials are available to the worker.

BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000")

def run_redteam_prompt_job_submission():
    print("Generating prompts...")
    prompts: list[RedTeamPrompt] = generate_redteam_prompts(seed=42)

    payload = {
        "prompts": [
            {
                "prompt": p.prompt,
                "category": p.category,
                "expected_pii_types": p.expected_pii_types,
            }
            for p in prompts
        ]
    }

    if len(prompts) > 0:
        print(f"Generated {len(prompts)} red-team prompts!")
        for prompt in prompts:
            print(f"- {prompt.category}: expected PII {prompt.expected_pii_types}")

    try:
        print("Submitting prompts to API...")
        response = requests.post(f"{BASE_URL}/eval/start", json=payload, timeout=5)
        response.raise_for_status()

        job = JobResponse.model_validate(response.json())
        total_tasks = job.total_tasks

        if total_tasks != len(prompts):
            print(f"Warning: submitted {len(prompts)} prompts, API created {total_tasks} tasks.")

        print(f"Prompts successfully submitted @ Job ID: {job.job_id} - Status: {job.status}")
        print(f"{BASE_URL}/eval/status/{job.job_id}?include_tasks=true")

    except requests.exceptions.RequestException as e:
        print(f"Error with FastAPI server: {e}")

    except ValidationError as e:
        print(f"Could not validate the response: {e}")

    except Exception as e:
        print(f"An error has occurred: {e}")

if __name__ == "__main__":
    run_redteam_prompt_job_submission()
