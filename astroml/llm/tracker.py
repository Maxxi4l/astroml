"""LLM Token Usage and Cost Tracking."""
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Mock cost per 1k tokens for different providers
COST_RATES = {
    "openai": {"prompt": 0.03, "completion": 0.06},
    "anthropic": {"prompt": 0.015, "completion": 0.075},
    "huggingface": {"prompt": 0.001, "completion": 0.001},
}

class LLMUsageTracker:
    """Tracks LLM API usage, costs, and latency."""

    def __init__(self):
        self.total_cost = 0.0
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.alert_threshold = 100.0  # $100

    def record_usage(
        self, provider_name: str, usage: Dict[str, int], latency_ms: float
    ) -> float:
        """
        Record usage for a request and calculate cost.
        Logs an alert if total cost exceeds the threshold.
        """
        rates = COST_RATES.get(provider_name.lower(), {"prompt": 0.0, "completion": 0.0})
        
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        
        cost = (prompt_tokens / 1000.0) * rates["prompt"] + (completion_tokens / 1000.0) * rates["completion"]
        
        self.total_prompt_tokens += prompt_tokens
        self.total_completion_tokens += completion_tokens
        self.total_cost += cost
        
        logger.info(
            "LLM Usage Recorded: Provider=%s, PromptTokens=%d, CompletionTokens=%d, Cost=$%.4f, Latency=%.2fms",
            provider_name, prompt_tokens, completion_tokens, cost, latency_ms
        )
        
        self.check_alerts()
        return cost

    def check_alerts(self):
        """Check if cost alerts should be triggered."""
        if self.total_cost > self.alert_threshold:
            logger.warning("LLM Cost Alert! Total cost ($%.2f) has exceeded threshold ($%.2f)", self.total_cost, self.alert_threshold)

    def get_summary(self) -> Dict[str, float]:
        """Get summary of tracking metrics."""
        return {
            "total_cost": self.total_cost,
            "total_prompt_tokens": self.total_prompt_tokens,
            "total_completion_tokens": self.total_completion_tokens,
            "total_tokens": self.total_prompt_tokens + self.total_completion_tokens
        }

# Global singleton tracker
global_tracker = LLMUsageTracker()
