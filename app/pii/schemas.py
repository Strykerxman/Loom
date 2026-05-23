from dataclasses import dataclass
from pydantic import BaseModel, Field


@dataclass(frozen=True)
class DetectedPII:
    type: str
    value: str
    normalized_value: str
    start_idx: int
    end_idx: int
    confidence: float
    source: str


class PIIEval(BaseModel): # result of pii evaluation for a given text input or output
    has_pii: bool
    types: list[str] = Field(default_factory=list)
    matches: dict[str, list[str]] = Field(default_factory=dict)
    risk_score: float = Field(le=1.0, ge=0.0)


class TaskEvaluationResult(BaseModel): # single task result
    input_eval: PIIEval
    output_eval: PIIEval
    output_leaked_pii: bool