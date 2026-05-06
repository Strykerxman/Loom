# LLM Evaluation Pipeline

## High-Level Overview

| Stage |             Task             |
|:-----:|:-----------------------------|
|   1   |                Send a prompt |
|   2   |            Receive the output|
|   3   |             Clean the output |
|   4   | Compare with expected result |

### Fan-out / Fan-in

1. **Fan-Out:** The FastAPI server will receive a Job with 1,000 prompts, for example. A Job record is created in the database. It then "fans out" by creating 1,000 Task records in the database and then pushes those prompts to a cache (eg. Redis). The API immediately returns `202 Accepted, Job ID: 0`  

2. **Processing (Isolation):** A predetermined amount of Python workers listen to the cache. They pull Tasks independently. If Task \#850 hits a rate limit from the LLM provider, the worker catches the error, increments `retry_count` on that Task, and places it back into the queue. The other 999 Tasks are unaffected, preventing a critical error and saving money on prompts (we don't have to send all 1000 prompts again).  

3. **Fan-In:** As workers finish, they update the Task rows in the database. The system will periodically check-in to see if all 1,000 Tasks linked to `Job ID: 0` are completed. If yes, the Job is marked as *done*.  

### Task Specifications

- **Atomicity:** A Task is either completed or failed. There is no half success.
- **Indempotency:** A failed Task can be restarted without causing problems. A worker will pick up the failed Task if it is available.
- **Independence:** A Task holds data (prompt, response, evaluation result). A Job manages the global progress (pending, running, done, failed), it does **not** touch any data.