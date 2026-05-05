from pydantic import BaseModel, Field
from typing import Any, Optional

class EvalRequest(BaseModel):

    prompts: list[str] = Field(min_length=1, max_length=1_000)

class TaskResponse(BaseModel):

    task_id: int
    status: str
    payload: dict[str, Any]
    response: Optional[dict[str, Any]] = None
    evaluation_result: Optional[dict[str, Any]] = None
    error_log: Optional[str] = None
    
class JobResponse(BaseModel):

    job_id: int
    status: str
    tasks: list[TaskResponse] = []
    total_tasks: int = 0
    completed_tasks: int = 0
