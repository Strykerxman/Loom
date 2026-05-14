from app.schemas import JobStatus


def derive_job_status(
    *,
    total_tasks: int,
    running_tasks: int,
    terminal_tasks: int,
) -> JobStatus:
    """Derive job progress from task counts.

    Job status describes pipeline progress, not whether every task succeeded.
    A job is `done` once every task is terminal. Failed task counts remain
    visible through `failed_tasks` on the API response.
    """
    if total_tasks <= 0:
        return "pending"

    if terminal_tasks >= total_tasks:
        return "done"

    if running_tasks > 0 or terminal_tasks > 0:
        return "running"

    return "pending"
