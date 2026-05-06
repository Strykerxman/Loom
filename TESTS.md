### End-to-End (E2E) Integration Test

Because *Loom* is a distributed, asynchronous system, traditional unit tests aren't sufficient to validate the entire workflow. Instead, we have an E2E test that simulates a real client interaction with the API, from job submission to result retrieval. This test ensures that all components of the system (API, database, workers) are working together correctly.  

The current test in [test_e2e.py](test_e2e.py) follows this logic:

1. **Job Submission (Fan-Out):** The test acts like a client, submits a batch of prompts to the `POST /eval/start` endpoint and receives a `job_id` (a Claim Ticket) in return.
2. **Async Polling:** Each background worker processes tasks independently (and simulate LLM latency). That means the test script must wait (further explanation below). *Polling* periodically checks the `GET /eval/status/{job_id}?include_tasks=false` endpoint.
    - It checks the status every 2 seconds.
    - It limits itself to 15 attempts (30 seconds total) to prevent infinite loops if the worker service is offline.
    - It prints the job's status, starting from "pending", transitioning to "running" and ending with "done" or "failed".
    - It prints the real-time `completed_tasks` vs `total_tasks`, i.e. the "Progress: x/3" for the test in [test_e2e.py](test_e2e.py)
*Note*: `include_tasks` is set to **false** to improve performance. We check the `tasks` array at the end.

3. **Result Validation (Fan-In):** When the Job is finished, the test inspects the `tasks` array returned in the JSON payload. It verifies that the worker(s) successfully evaluated the prompts, detected the PII and saved the structured `evaluation_result` JSON to the database.