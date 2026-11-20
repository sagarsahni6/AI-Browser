from typing import Optional, Tuple
from backend.app.ai.providers.base import BaseAIProvider
from backend.app.ai.registry import provider_registry
from backend.app.config import settings

class ModelRouter:
    @staticmethod
    def route_for_task(
        task_type: str = "text", # text, vision, tools, chart, canvas, reasoning, finance, research
        preferred_provider: Optional[str] = None,
        preferred_model: Optional[str] = None
    ) -> Tuple[BaseAIProvider, str]:
        provider = provider_registry.get(preferred_provider)

        if preferred_model:
            return provider, preferred_model

        pid = provider.provider_id

        if pid == "nvidia_nim":
            if task_type in ("vision", "chart", "canvas"):
                model = settings.NVIDIA_VISION_MODEL
            elif task_type in ("reasoning", "finance", "synthesis"):
                model = settings.NVIDIA_REASONING_MODEL
            else:
                model = settings.NVIDIA_MODEL

        elif pid == "anthropic":
            model = getattr(settings, "ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")

        elif pid == "google_gemini":
            model = getattr(settings, "GOOGLE_MODEL", "gemini-2.0-flash")

        elif pid == "groq":
            model = getattr(settings, "GROQ_MODEL", "llama-3.3-70b-versatile")

        elif pid == "ollama":
            if task_type in ("vision", "chart"):
                model = "llava"
            else:
                model = getattr(settings, "OLLAMA_MODEL", "llama3.2")

        else:
            # openai_compatible or generic fallback
            model = settings.OPENAI_MODEL

        return provider, model
