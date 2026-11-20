import json
import httpx
from typing import AsyncGenerator, Dict, List, Optional, Any
from backend.app.ai.providers.base import BaseAIProvider, ChatCompletionResult
from backend.app.ai.capabilities import ModelCapabilities
from backend.app.config import settings

class OllamaProvider(BaseAIProvider):
    def __init__(self, base_url: Optional[str] = None, default_model: Optional[str] = None):
        self._base_url = (base_url or getattr(settings, "OLLAMA_BASE_URL", "http://localhost:11434")).rstrip("/")
        self._default_model = default_model or getattr(settings, "OLLAMA_MODEL", "llama3.2")

    @property
    def provider_id(self) -> str:
        return "ollama"

    @property
    def name(self) -> str:
        return "Ollama (Local)"

    def get_capabilities(self, model: str) -> ModelCapabilities:
        return ModelCapabilities(
            supports_text=True,
            supports_vision=True if "vision" in model.lower() or "llava" in model.lower() else False,
            supports_tools=True,
            supports_json=True,
            context_window=32768
        )

    async def check_connection(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(f"{self._base_url}/api/tags")
                return res.status_code == 200
        except Exception:
            return False

    async def list_models(self) -> List[str]:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(f"{self._base_url}/api/tags")
                if res.status_code == 200:
                    data = res.json()
                    return [m["name"] for m in data.get("models", [])]
        except Exception:
            pass
        return ["llama3.2", "mistral", "qwen2.5", "llava"]

    async def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> ChatCompletionResult:
        target_model = model or self._default_model
        payload = {
            "model": target_model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }
        if tools:
            payload["tools"] = tools

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(f"{self._base_url}/api/chat", json=payload)
                resp.raise_for_status()
                data = resp.json()
                msg = data.get("message", {})
                return ChatCompletionResult(
                    content=msg.get("content", ""),
                    model=target_model,
                    tool_calls=msg.get("tool_calls")
                )
        except Exception as e:
            return ChatCompletionResult(
                content=f"[Ollama ({target_model})] Error connecting to local Ollama at {self._base_url}: {e}",
                model=target_model
            )

    async def stream_completion(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> AsyncGenerator[str, None]:
        target_model = model or self._default_model
        payload = {
            "model": target_model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }
        if tools:
            payload["tools"] = tools

        try:
            async with httpx.AsyncClient(timeout=90.0) as client:
                async with client.stream("POST", f"{self._base_url}/api/chat", json=payload) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        try:
                            chunk = json.loads(line)
                            content = chunk.get("message", {}).get("content")
                            if content:
                                yield content
                        except Exception:
                            pass
        except Exception as e:
            yield f"[Ollama Error: {e}]"

    async def analyze_image(
        self,
        image_base64: str,
        prompt: str,
        model: Optional[str] = None
    ) -> str:
        target_model = model or "llava"
        raw_b64 = image_base64.split(",", 1)[-1] if "," in image_base64 else image_base64
        payload = {
            "model": target_model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                    "images": [raw_b64]
                }
            ],
            "stream": False
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(f"{self._base_url}/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data.get("message", {}).get("content", "")
