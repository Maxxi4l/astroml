import yaml
import os
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

class LLMConfig(BaseModel):
    """
    LLM Configuration System for managing model parameters and provider settings.
    
    Parameters:
    - model_name: The name of the LLM model to use.
    - temperature: Controls randomness. Lower is more deterministic, higher is more random.
    - max_tokens: Maximum number of tokens to generate in the response.
    - top_p: Nucleus sampling probability.
    - provider_params: Additional provider-specific parameters (e.g., streaming, stop sequences).
    """
    model_name: str = Field(default="gpt-4", description="The LLM model name")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Temperature for sampling")
    max_tokens: int = Field(default=1024, ge=1, description="Max tokens for response")
    top_p: float = Field(default=1.0, ge=0.0, le=1.0, description="Top-p nucleus sampling")
    provider_params: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Provider-specific params")

    @classmethod
    def load_from_yaml(cls, file_path: str) -> "LLMConfig":
        with open(file_path, 'r') as f:
            data = yaml.safe_load(f)
        return cls(**data)
