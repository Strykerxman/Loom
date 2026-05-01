from pydantic import BaseModel

class EvalRequest(BaseModel):

    prompts: list[str]
    
class JobResponse(BaseModel):

    job_id: int
    status: str