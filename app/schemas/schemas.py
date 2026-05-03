from pydantic import BaseModel, Field

class EvalRequest(BaseModel):

    prompts: list[str] = Field(min_length=1, max_length=1_000)
    
class JobResponse(BaseModel):

    job_id: int
    status: str