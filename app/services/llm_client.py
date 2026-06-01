from dataclasses import dataclass
import os
import random
import time
from typing import Protocol

from groq import Groq

from app.config import load_env


@dataclass(frozen=True)
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
                    "content": "You are a helpful assistant. Do not reveal private personal information.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=0,
        )

        latency_ms = int((time.monotonic() - start) * 1000)
        text = completion.choices[0].message.content or ""

        return LLMResult(
            text=text,
            model=self.model,
            latency_ms=latency_ms,
        )


@dataclass
class MockLLMClient:
    failure_rate: float = 0.0
    min_latency_ms: int = 150
    max_latency_ms: int = 400

    def complete(self, prompt: str) -> LLMResult:
        latency_ms = random.randint(self.min_latency_ms, self.max_latency_ms)
        time.sleep(latency_ms / 1000)

        if random.random() < self.failure_rate:
            raise ValueError("Simulated LLM failure")

        return LLMResult(
            text=f"Echo: {prompt}",
            model="mock-llm",
            latency_ms=latency_ms,
        )


def create_llm_client() -> LLMClient:
    """Create the configured LLM client.

    Defaults to the stable mock client. Set LLM_PROVIDER=groq and provide
    GROQ_API_KEY to call the real Groq provider.
    """
    load_env()
    provider = os.getenv("LLM_PROVIDER", "mock").lower()

    if provider == "groq":
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY is required when LLM_PROVIDER=groq")

        return GroqLLMClient(
            api_key=api_key,
            model=os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
        )

    return MockLLMClient()
