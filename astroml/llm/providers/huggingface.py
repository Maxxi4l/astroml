"""HuggingFace Provider."""
from typing import Any, Dict
from .base import LLMProvider

class HuggingFaceProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "meta-llama/Llama-2-7b-chat-hf"):
        self.api_key = api_key
        self.model = model
        self.last_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    def generate(self, prompt: str, **kwargs: Any) -> str:
        # Mock implementation for HuggingFace generate
        self.last_usage = {"prompt_tokens": 15, "completion_tokens": 25, "total_tokens": 40}
        return f"HuggingFace ({self.model}) response to: {prompt}"

    def get_token_usage(self) -> Dict[str, int]:
        return self.last_usage
