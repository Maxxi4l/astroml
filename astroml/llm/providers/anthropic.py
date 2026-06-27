"""Anthropic Provider."""
from typing import Any, Dict
from .base import LLMProvider

class AnthropicProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "claude-3-opus-20240229"):
        self.api_key = api_key
        self.model = model
        self.last_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    def generate(self, prompt: str, **kwargs: Any) -> str:
        import anthropic

        client = anthropic.Anthropic(api_key=self.api_key)
        max_tokens = kwargs.pop("max_tokens", 1024)
        response = client.messages.create(
            model=kwargs.pop("model", self.model),
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
            **kwargs,
        )
        if response.usage is not None:
            self.last_usage = {
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
            }
        return "".join(block.text for block in response.content if hasattr(block, "text"))

    def get_token_usage(self) -> Dict[str, int]:
        return self.last_usage
