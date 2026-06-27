"""Base LLM Provider."""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def generate(self, prompt: str, **kwargs: Any) -> str:
        """Generate a response from the LLM."""
        pass

    @abstractmethod
    def get_token_usage(self) -> Dict[str, int]:
        """Return the token usage for the last generation."""
        pass
