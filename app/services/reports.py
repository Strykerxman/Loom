from typing import get_args

from app.models import JobTable, TaskTable
from app.schemas import JobStatus, JobLeakageReport, TaskEvaluationResult
from .redteam_prompts import CATEGORIES

def build_job_leakage_report(job: JobTable, *, status: JobStatus) -> JobLeakageReport:
    tasks = job.tasks
    tot_tasks: int = 0
    evaluated_tasks: int = 0

    report = JobLeakageReport(
        job_id=job.job_id,
        status=status,
    )

    for task in tasks:
        task: TaskTable

        payload = task.payload
        category = payload.get("category", "uncategorized")

        if category not in get_args(CATEGORIES):
            print(f"Warning: Category {category} is not supported.")
        
        tot_tasks += 1

        task_eval_result = task.evaluation_result

        if task_eval_result is None: continue

        valid_eval_result = TaskEvaluationResult.model_validate(task_eval_result)

        evaluated_tasks += 1


