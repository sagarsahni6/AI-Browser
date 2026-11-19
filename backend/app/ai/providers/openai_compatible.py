import json
import httpx
from typing import AsyncGenerator, Dict, List, Optional, Any
from backend.app.ai.providers.base import BaseAIProvider, ChatCompletionResult
from backend.app.ai.capabilities import ModelCapabilities, get_model_capabilities
from backend.app.config import settings

class OpenAICompatibleProvider(BaseAIProvider):
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, default_model: Optional[str] = None):
        self._api_key = api_key or settings.OPENAI_API_KEY
        self._base_url = (base_url or settings.OPENAI_BASE_URL).rstrip("/")
        self._default_model = default_model or settings.OPENAI_MODEL

    @property
    def provider_id(self) -> str:
        return "openai_compatible"

    @property
    def name(self) -> str:
        return "OpenAI Compatible"

    def get_capabilities(self, model: str) -> ModelCapabilities:
        return get_model_capabilities(model or self._default_model)

    async def check_connection(self) -> bool:
        if not self._api_key:
            return False
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(
                    f"{self._base_url}/models",
                    headers={"Authorization": f"Bearer {self._api_key}"}
                )
                return res.status_code == 200
        except Exception:
            return False

    async def list_models(self) -> List[str]:
        if not self._api_key:
            return [self._default_model]
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                res = await client.get(
                    f"{self._base_url}/models",
                    headers={"Authorization": f"Bearer {self._api_key}"}
                )
                if res.status_code == 200:
                    data = res.json()
                    return [m["id"] for m in data.get("data", []) if "id" in m]
        except Exception:
            pass
        return [self._default_model]

    async def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> ChatCompletionResult:
        target_model = model or self._default_model

        if not self._api_key:
            return ChatCompletionResult(
                content="[OpenAI Compatible] Ready. To enable live inference, configure your API key in Settings.",
                model=target_model
            )

        payload: Dict[str, Any] = {
            "model": target_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False
        }
        if tools:
            payload["tools"] = tools

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{self._base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json"
                },
                json=payload
            )
            resp.raise_for_status()
            data = resp.json()
            choice = data["choices"][0]
            msg = choice.get("message", {})
            return ChatCompletionResult(
                content=msg.get("content") or "",
                model=data.get("model", target_model),
                tool_calls=msg.get("tool_calls"),
                finish_reason=choice.get("finish_reason"),
                usage=data.get("usage")
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

        if not self._api_key:
            offline_msg = f"[OpenAI ({target_model})] Ready. Set your API key to activate live streaming."
            for word in offline_msg.split(" "):
                yield word + " "
            return

        payload: Dict[str, Any] = {
            "model": target_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True
        }
        if tools:
            payload["tools"] = tools

        async with httpx.AsyncClient(timeout=90.0) as client:
            async with client.stream(
                "POST",
                f"{self._base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json"
                },
                json=payload
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    line = line.strip()
                    if not line or line.startswith(":"):
                        continue
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data_str)
                            delta = chunk["choices"][0].get("delta", {})
                            content = delta.get("content")
                            if content:
                                yield content
                        except Exception:
                            pass

    async def analyze_image(
        self,
        image_base64: str,
        prompt: str,
        model: Optional[str] = None
    ) -> str:
        target_model = model or self._default_model
        if not image_base64.startswith("data:"):
            image_url = f"data:image/png;base64,{image_base64}"
        else:
            image_url = image_base64

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": image_url}}
                ]
            }
        ]

        result = await self.chat_completion(messages=messages, model=target_model)
        return result.content
