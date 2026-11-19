from typing import Optional, Tuple
from backend.app.ai.providers.base import BaseAIProvider
from backend.app.ai.registry import provider_registry
from backend.app.config import settings

class ModelRouter:
    @staticmethod
    def route_for_task(
        task_type: str = "text", # text, vision, tools, research
        preferred_provider: Optional[str] = None,
        preferred_model: Optional[str] = None
    ) -> Tuple[BaseAIProvider, str]:
        provider = provider_registry.get(preferred_provider)

        if preferred_model:
            return provider, preferred_model

        if task_type == "vision":
            model = settings.NVIDIA_VISION_MODEL if provider.provider_id == "nvidia_nim" else "gpt-4o"
        elif task_type in ("tools", "research"):
            model = settings.NVIDIA_MODEL if provider.provider_id == "nvidia_nim" else settings.OPENAI_MODEL
        else:
            # Default text
            model = settings.NVIDIA_MODEL if provider.provider_id == "nvidia_nim" else settings.OPENAI_MODEL

        return provider, model
