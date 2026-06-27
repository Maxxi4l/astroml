"""Factory for LLM Providers."""
import os
from typing import Dict, Type
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
    """Get the configured LLM provider."""
    provider_name = provider_name or os.getenv("LLM_PROVIDER", "openai").lower()
    
    if provider_name not in _PROVIDERS:
        raise ValueError(f"Unknown LLM provider: {provider_name}")
    
    provider_class = _PROVIDERS[provider_name]
    
    # Extract API key based on provider
    api_key = kwargs.pop("api_key", None)
    if not api_key:
        env_key = f"{provider_name.upper()}_API_KEY"
        api_key = os.getenv(env_key, f"mock-{provider_name}-key")

    return provider_class(api_key=api_key, **kwargs)
