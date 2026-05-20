from pydantic import ValidationError

from app.models import JobTable, TaskTable
from app.schemas import CategoryLeakageReport, JobStatus, JobLeakageReport, TaskEvaluationResult


def build_job_leakage_report(job: JobTable, *, status: JobStatus) -> JobLeakageReport:
    
    report = JobLeakageReport(
        job_id=job.job_id,
        status=status,
    )

    for task in job.tasks:
        task: TaskTable

        category = task.payload.get("category", "uncategorized")
        
        category_report = report.by_category.setdefault(
            category,
            CategoryLeakageReport(category=category)
        )

        report.total_tasks += 1
        category_report.total_tasks += 1

        task_eval_result = task.evaluation_result

        if task_eval_result is None: 
            continue

        try: 
            valid_eval_result = TaskEvaluationResult.model_validate(task_eval_result)
        except ValidationError:
            print(f"Warning: Task {task.task_id} has invalid evaluation result format.")
            continue

        _apply_eval_counts(report, valid_eval_result)
        _apply_eval_counts(category_report, valid_eval_result)

    _apply_leak_rate(report)

    # each category leak rate
    for category_report in report.by_category.values():
        _apply_leak_rate(category_report)

    return report


def _apply_eval_counts(
        report_like: JobLeakageReport | CategoryLeakageReport, 
        eval_result: TaskEvaluationResult
    ) -> None:
    
    report_like.evaluated_tasks += 1

    if eval_result.input_eval.has_pii:
        report_like.input_pii_tasks += 1
    
    if eval_result.output_eval.has_pii:
        report_like.output_pii_tasks += 1

    if eval_result.output_leaked_pii:
        report_like.leaked_tasks += 1


def _apply_leak_rate(
        report_like: JobLeakageReport | CategoryLeakageReport
    ) -> None:

    if report_like.evaluated_tasks == 0:
        report_like.leak_rate = 0.0
    else:
        report_like.leak_rate = report_like.leaked_tasks / report_like.evaluated_tasks