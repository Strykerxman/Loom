from abc import ABC, abstractmethod
from app.pii.schemas import DetectedPII


class BaseDetector(ABC):
    @property
    @abstractmethod
    def type(self) -> str:
        pass


    @abstractmethod
    def detect(self, text: str) -> list[DetectedPII]:
        pass