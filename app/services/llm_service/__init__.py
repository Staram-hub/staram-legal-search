from abc import ABC, abstractmethod
from typing import Any


class AIModel(ABC):
    """Abstract base class for LLM models."""

    @abstractmethod
    async def run(
        self, system_prompt: str, prompt: str, temperature: float, **kwargs
    ) -> dict[str, Any]:
        pass


class BaseEmbedder(ABC):
    """Abstract base class for embedding models."""

    @abstractmethod
    async def embed_text(self, input_text: str) -> list[float]:
        pass
