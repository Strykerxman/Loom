from app.services.redteam_prompts import generate_redteam_prompts, RedTeamPrompt
# Purpose:
# Submit Loom's generated red-team prompt suite to a running FastAPI server.

# Preconditions:
# - Docker/Postgres is running.
# - Uvicorn server is running.
# - At least one worker is running.
# - The worker has access to the same environment variables as the API.
# - If using Groq, GROQ credentials are available to the worker.

def run_redteam_prompt_job_submission():
    prompts: list[RedTeamPrompt] = generate_redteam_prompts(seed=42)

    payload = {
        "prompts": [
            p.prompt for p in prompts
        ]
    }
