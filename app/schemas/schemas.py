from pydantic import BaseModel, Field, ConfigDict
from typing import Any, Optional, Literal

TaskStatus = Literal["pending", "running", "done", "failed"]
JobStatus = Literal["pending", "running", "done"]


class PIIEval(BaseModel):
    has_pii: bool
    types: list[str] = Field(default_factory=list)
    matches: dict[str, list[str]] = Field(default_factory=dict)
    risk_score: float = Field(le=1.0, ge=0.0)


class TaskEvaluationResult(BaseModel): # single task result
    input_eval: PIIEval
    output_eval: PIIEval
    output_leaked_pii: bool


class EvalPrompt(BaseModel): # prompt schema, payload
    prompt: str = Field(min_length=1)
    category: Optional[str] = None
    expected_pii_types: list[str] = Field(default_factory=list)


class EvalRequest(BaseModel): # submit prompts to api to be evaluated
    prompts: list[str | EvalPrompt] = Field(min_length=1, max_length=1_000)


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    task_id: int
    status: TaskStatus
    payload: dict[str, Any]
    response: Optional[dict[str, Any]] = None
    evaluation_result: Optional[TaskEvaluationResult] = None
    error_log: Optional[str] = None


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    job_id: int
    status: JobStatus
    tasks: list[TaskResponse] = Field(default_factory=list)
    total_tasks: int = 0
    finished_tasks: int = 0 # terminal tasks: status in ["done", "failed"]
    failed_tasks: int = 0 # terminal failures: status = "failed"


class CategoryLeakageReport(BaseModel):
    category: str
    total_tasks: int = 0
    evaluated_tasks: int = 0
    input_pii_tasks: int = 0
    output_pii_tasks: int = 0
    leaked_tasks: int = 0
    leak_rate: float = 0.0


class JobLeakageReport(BaseModel): # 
    job_id: int
    status: JobStatus

    total_tasks: int = 0
    evaluated_tasks: int = 0

    input_pii_tasks: int = 0
    output_pii_tasks: int = 0
    leaked_tasks: int = 0
    leak_rate: float = 0.0

    by_category: dict[str, CategoryLeakageReport] = Field(default_factory=dict)