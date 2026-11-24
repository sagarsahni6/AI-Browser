import time
import logging
from enum import Enum
from typing import Optional, Tuple, Dict, Any, Union
from backend.app.ai.providers.base import BaseAIProvider
from backend.app.ai.registry import provider_registry
from backend.app.config import settings

logger = logging.getLogger("model_router")

class TaskType(str, Enum):
    VISION = "vision"
    TOOL_CALLING = "tools"
    REASONING = "reasoning"
    GENERAL = "text"
    RESEARCH = "research"
    CHART = "chart"
    CANVAS = "canvas"
    FINANCE = "finance"

class ProviderCircuitBreaker:
    """Tracks consecutive provider failures and opens circuit for a cooldown period."""

    def __init__(self, failure_threshold: int = 3, cooldown_seconds: float = 30.0):
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self._failures: Dict[str, int] = {}
        self._tripped_at: Dict[str, float] = {}

    def record_success(self, provider_id: str) -> None:
        self._failures[provider_id] = 0
        self._tripped_at.pop(provider_id, None)

    def record_failure(self, provider_id: str) -> None:
        count = self._failures.get(provider_id, 0) + 1
        self._failures[provider_id] = count
        if count >= self.failure_threshold:
            self._tripped_at[provider_id] = time.time()
            logger.warning(f"Circuit breaker TRIPPED for provider '{provider_id}' (failures: {count})")

    def is_available(self, provider_id: str) -> bool:
        tripped = self._tripped_at.get(provider_id)
        if not tripped:
            return True
        if time.time() - tripped > self.cooldown_seconds:
            # Cooldown passed, half-open
            self._failures[provider_id] = 0
            self._tripped_at.pop(provider_id, None)
            logger.info(f"Circuit breaker reset for provider '{provider_id}' after cooldown.")
            return True
        return False

# Global circuit breaker instance
circuit_breaker = ProviderCircuitBreaker()

class ModelRouter:
    @staticmethod
    def route_for_task(
        task_type: Union[str, TaskType] = "text",
        preferred_provider: Optional[str] = None,
        preferred_model: Optional[str] = None
    ) -> Tuple[BaseAIProvider, str]:
        # Normalize task_type string
        t_type = task_type.value if isinstance(task_type, TaskType) else str(task_type).lower()

        # 1. Preferred provider explicitly requested
        if preferred_provider:
            provider = provider_registry.get(preferred_provider)
            model = preferred_model or ModelRouter._select_model_for_provider(provider.provider_id, t_type)
            return provider, model

        if preferred_model:
            provider = provider_registry.get()
            return provider, preferred_model

        # 2. Primary Provider: NVIDIA NIM (if circuit closed)
        if circuit_breaker.is_available("nvidia_nim"):
            provider = provider_registry.get("nvidia_nim")
            model = ModelRouter._select_model_for_provider("nvidia_nim", t_type)
            return provider, model

        # 3. Failover Sequence: Secondary Providers
        secondary_candidates = ["openai_compatible", "anthropic", "groq", "google_gemini", "ollama"]
        for cand in secondary_candidates:
            if circuit_breaker.is_available(cand):
                cand_provider = provider_registry.get(cand)
                # Verify provider has active API key or connection
                if getattr(cand_provider, "_api_key", None) or cand == "ollama":
                    model = ModelRouter._select_model_for_provider(cand, t_type)
                    logger.info(f"Failing over to secondary provider '{cand}' with model '{model}'")
                    return cand_provider, model

        # 4. Fallback to default registered provider
        provider = provider_registry.get()
        model = ModelRouter._select_model_for_provider(provider.provider_id, t_type)
        return provider, model

    @staticmethod
    def _select_model_for_provider(provider_id: str, task_type: str) -> str:
        if provider_id == "nvidia_nim":
            if task_type in ("vision", "chart", "canvas"):
                return settings.NVIDIA_VISION_MODEL
            elif task_type in ("reasoning", "finance", "synthesis"):
                return settings.NVIDIA_REASONING_MODEL
            elif task_type in ("lightweight", "fast"):
                return getattr(settings, "NVIDIA_LIGHTWEIGHT_MODEL", "meta/llama-3.1-8b-instruct")
            else:
                return settings.NVIDIA_MODEL

        elif provider_id == "anthropic":
            return getattr(settings, "ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")

        elif provider_id == "google_gemini":
            return getattr(settings, "GOOGLE_MODEL", "gemini-2.0-flash")

        elif provider_id == "groq":
            return getattr(settings, "GROQ_MODEL", "llama-3.3-70b-versatile")

        elif provider_id == "ollama":
            if task_type in ("vision", "chart"):
                return "llava"
            return getattr(settings, "OLLAMA_MODEL", "llama3.2")

        else:
            return settings.OPENAI_MODEL
