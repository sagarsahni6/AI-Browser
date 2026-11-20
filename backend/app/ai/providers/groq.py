from typing import Optional, List
from backend.app.ai.providers.openai_compatible import OpenAICompatibleProvider
from backend.app.config import settings

class GroqProvider(OpenAICompatibleProvider):
    def __init__(self, api_key: Optional[str] = None, default_model: Optional[str] = None):
        super().__init__(
            api_key=api_key or getattr(settings, "GROQ_API_KEY", None),
            base_url="https://api.groq.com/openai/v1",
            default_model=default_model or getattr(settings, "GROQ_MODEL", "llama-3.3-70b-versatile")
        )

    @property
    def provider_id(self) -> str:
        return "groq"

    @property
    def name(self) -> str:
        return "Groq (Ultra-Fast)"

    async def list_models(self) -> List[str]:
        return [
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "mixtral-8x7b-32768",
            "gemma2-9b-it"
        ]
