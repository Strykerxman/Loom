from pydantic import BaseModel, Field, ConfigDict
from typing import Any, Optional, Literal

class PIIEval(BaseModel):
    has_pii: bool
    types: list[str] = Field(default_factory=list)
    matches: dict[str, list[str]] = Field(default_factory=dict)
    risk_score: float = Field(le=1.0, ge=0.0)

class EvalRequest(BaseModel):
    prompts: list[str] = Field(min_length=1, max_length=1_000)

class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    task_id: int
    status: Literal["pending", "running", "done", "failed"]
    payload: dict[str, Any]
    response: Optional[dict[str, Any]] = None
    evaluation_result: Optional[PIIEval] = None # This field will hold the PII evaluation result, it's optional because it won't be populated until after the worker processes the task
    error_log: Optional[str] = None
    
class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    job_id: int
    status: Literal["pending", "running", "done", "failed"]
    tasks: list[TaskResponse] = Field(default_factory=list) # Lists are mutable, so we use default_factory to avoid shared mutable defaults. 
    # Even if include_tasks=false, we want to return an empty list rather than None for consistency in the response schema, and it also simplifies the frontend handling of the response since they can always expect a list.    
    total_tasks: int = 0 # Intentionally simple, avoids empty tasks list if include_tasks=false, and allows us to track progress even if we don't include task details in the response
    finished_tasks: int = 0 # status in ["done", "failed"]
    failed_tasks: int = 0 # status = "failed"