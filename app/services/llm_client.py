from dataclasses import dataclass
import os
import random
import time
from typing import Protocol
from groq import Groq

from app.config import load_env

@dataclass(frozen=True) # frozen=True means that it doesnt evolve over time. true because we only get 1 result and it shouldnt be modified
# also means it can be Hashed, i.e. two LLMResult objects with same content are equal, their mem address doesnt affect equality.
class LLMResult:
    text: str
    model: str
    latency_ms: int

class LLMClient(Protocol):
    def complete(self, prompt: str) -> LLMResult:
        ...


@dataclass
class GroqLLMClient(LLMClient):
    api_key: str
    model: str = "llama-3.1-8b-instant"

    def complete(self, prompt: str) -> LLMResult:
        start = time.monotonic()

        client = Groq(api_key=self.api_key)

        completion = client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant. Do not reveal private personal information."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0
        )

        latency_ms = int((time.monotonic() - start) * 1000)
        text = completion.choices[0].message.content or ""

        return LLMResult(
            text=text,
            model=self.model,
            latency_ms=latency_ms
        )
        

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
    

def create_llm_client() -> LLMClient:
    """
    Reads .env file for a provider and its associated API key.

    Creates a GroqLLMClient if the LLM_PROVIDER=groq.

    Defaults to a MockLLMClient in all other cases.
    """
    provider = os.getenv("LLM_PROVIDER", "mock")
    
    if provider == "groq":
        api_key = os.environ["GROQ_API_KEY"] #os.environ because api_key is critical, will raise valueerror if not found
        model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
        return GroqLLMClient(
            api_key=api_key,
            model=model,
        )
    
    else:
        return MockLLMClient()
    