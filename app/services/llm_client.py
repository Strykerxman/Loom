from dataclasses import dataclass
import random
import time
from typing import Protocol

@dataclass(frozen=True) # frozen=True means that it doesnt evolve over time. true because we only get 1 result and it shouldnt be modified
# also means it can be Hashed, i.e. two LLMResult objects with same content are equal, their mem address doesnt affect equality.
class LLMResult:
    text: str
    model: str
    latency_ms: int

class LLMClient(Protocol):
    def complete(self, prompt: str) -> LLMResult:
        ...

@dataclass # not frozen as may be modified directly in testing
class MockLLMClient:
    failure_rate: float = 0.3
    min_latency_ms: int = 2000
    max_latency_ms: int = 5000
    
    def complete(self, prompt: str) -> LLMResult:
        latency_ms=random.randint(self.min_latency_ms, self.max_latency_ms)
        time.sleep(latency_ms / 1000)

        if random.random() < self.failure_rate:
            raise ValueError("Simulated LLM failure")
        
        return LLMResult(
            text=f"Echo: {prompt}",
            model="mock-llm",
            latency_ms=latency_ms
        )