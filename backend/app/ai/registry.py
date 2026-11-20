from typing import Dict, Optional, List
from backend.app.ai.providers.base import BaseAIProvider
from backend.app.ai.providers.nvidia_nim import NvidiaNimProvider
from backend.app.ai.providers.openai_compatible import OpenAICompatibleProvider
from backend.app.ai.providers.anthropic import AnthropicProvider
from backend.app.ai.providers.google_gemini import GoogleGeminiProvider
from backend.app.ai.providers.groq import GroqProvider
from backend.app.ai.providers.ollama import OllamaProvider
from backend.app.config import settings

class ProviderRegistry:
    def __init__(self):
        self._providers: Dict[str, BaseAIProvider] = {}
        self._primary_id = getattr(settings, "DEFAULT_PROVIDER", "nvidia_nim")
        self._initialize_default_providers()

    def _initialize_default_providers(self):
        self.register(NvidiaNimProvider())
        self.register(OpenAICompatibleProvider())
        self.register(AnthropicProvider())
        self.register(GoogleGeminiProvider())
        self.register(GroqProvider())
        self.register(OllamaProvider())

    def register(self, provider: BaseAIProvider):
        self._providers[provider.provider_id] = provider

    def get(self, provider_id: Optional[str] = None) -> BaseAIProvider:
        pid = provider_id or self._primary_id
        if pid in self._providers:
            return self._providers[pid]
        # Fallback to primary if specified ID is not found
        return self._providers.get(self._primary_id, list(self._providers.values())[0])

    def get_primary(self) -> BaseAIProvider:
        return self._providers.get(self._primary_id, list(self._providers.values())[0])

    def list_providers(self) -> List[BaseAIProvider]:
        return list(self._providers.values())

provider_registry = ProviderRegistry()
