"""HuggingFace Provider."""
from typing import Any, Dict
from .base import LLMProvider

class HuggingFaceProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "meta-llama/Llama-2-7b-chat-hf"):
        self.api_key = api_key
        self.model = model
        self.last_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    def generate(self, prompt: str, **kwargs: Any) -> str:
        from huggingface_hub import InferenceClient

        client = InferenceClient(model=kwargs.pop("model", self.model), token=self.api_key)
        text = client.text_generation(prompt, **kwargs)

        # The inference API doesn't report usage, so approximate (~4 chars/token).
        prompt_tokens = max(1, len(prompt) // 4)
        completion_tokens = max(1, len(text) // 4)
        self.last_usage = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        }
        return text

    def get_token_usage(self) -> Dict[str, int]:
        return self.last_usage
