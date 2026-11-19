from abc import ABC, abstractmethod
from typing import AsyncGenerator, Dict, List, Optional, Any
from pydantic import BaseModel
from backend.app.ai.capabilities import ModelCapabilities

class ChatCompletionResult(BaseModel):
    content: str
    model: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    finish_reason: Optional[str] = None
    usage: Optional[Dict[str, Any]] = None

class BaseAIProvider(ABC):
    @property
    @abstractmethod
    def provider_id(self) -> str:
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    async def check_connection(self) -> bool:
        pass

    @abstractmethod
    async def list_models(self) -> List[str]:
        pass

    @abstractmethod
    async def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> ChatCompletionResult:
        pass

    @abstractmethod
    async def stream_completion(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> AsyncGenerator[str, None]:
        pass

    @abstractmethod
    async def analyze_image(
        self,
        image_base64: str,
        prompt: str,
        model: Optional[str] = None
    ) -> str:
        pass

    @abstractmethod
    def get_capabilities(self, model: str) -> ModelCapabilities:
        pass
