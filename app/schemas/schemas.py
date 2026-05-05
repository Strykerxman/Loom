from pydantic import BaseModel, Field

class EvalRequest(BaseModel):

    prompts: list[str] = Field(min_length=1, max_length=1_000)
    
class JobResponse(BaseModel):

    job_id: int
    status: str
    total_tasks: int = 0
    completed_tasks: int = 0