"""OpenAI Provider."""
from typing import Any, Dict
from .base import LLMProvider

class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "gpt-4"):
        self.api_key = api_key
        self.model = model
        self.last_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    def generate(self, prompt: str, **kwargs: Any) -> str:
        # Mock implementation for OpenAI generate
        self.last_usage = {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
        return f"OpenAI ({self.model}) response to: {prompt}"

    def get_token_usage(self) -> Dict[str, int]:
        return self.last_usage
