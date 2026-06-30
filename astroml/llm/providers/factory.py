"""Factory for LLM Providers."""
import os
from typing import Dict, Type

from astroml.llm.provider import MockLLMProvider
from .base import LLMProvider
from .openai import OpenAIProvider
from .anthropic import AnthropicProvider
from .huggingface import HuggingFaceProvider

_PROVIDERS: Dict[str, Type[LLMProvider]] = {
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "huggingface": HuggingFaceProvider,
}


def get_llm_provider(provider_name: str = None, **kwargs) -> LLMProvider:
    """Get the configured LLM provider.

    Falls back to the built-in mock provider unless an explicit provider key is
    configured. This prevents runtime failures when the environment is missing
    credentials for an external LLM service.
    """
    provider_name = provider_name or os.getenv("LLM_PROVIDER", "openai").lower()

    if provider_name not in _PROVIDERS:
        raise ValueError(f"Unknown LLM provider: {provider_name}")

    api_key = kwargs.pop("api_key", None)
    env_key = f"{provider_name.upper()}_API_KEY"
    configured_key = api_key or os.getenv(env_key)

    if configured_key:
        provider_class = _PROVIDERS[provider_name]
        return provider_class(api_key=configured_key, **kwargs)

    return MockLLMProvider()
