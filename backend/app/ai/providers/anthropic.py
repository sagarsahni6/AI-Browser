import json
import httpx
from typing import AsyncGenerator, Dict, List, Optional, Any
from backend.app.ai.providers.base import BaseAIProvider, ChatCompletionResult
from backend.app.ai.capabilities import ModelCapabilities
from backend.app.config import settings

class AnthropicProvider(BaseAIProvider):
    def __init__(self, api_key: Optional[str] = None, default_model: Optional[str] = None):
        self._api_key = api_key or getattr(settings, "ANTHROPIC_API_KEY", None)
        self._default_model = default_model or getattr(settings, "ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")
        self._base_url = "https://api.anthropic.com/v1"

    @property
    def provider_id(self) -> str:
        return "anthropic"

    @property
    def name(self) -> str:
        return "Anthropic Claude"

    def get_capabilities(self, model: str) -> ModelCapabilities:
        return ModelCapabilities(
            supports_text=True,
            supports_vision=True,
            supports_tools=True,
            supports_json=True,
            context_window=200000
        )

    async def check_connection(self) -> bool:
        if not self._api_key:
            return False
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(
                    f"{self._base_url}/models",
                    headers={
                        "x-api-key": self._api_key,
                        "anthropic-version": "2023-06-01"
                    }
                )
                return res.status_code == 200
        except Exception:
            return False

    async def list_models(self) -> List[str]:
        return [
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022",
            "claude-3-opus-20240229"
        ]

    def _convert_messages(self, messages: List[Dict[str, Any]]):
        system_prompt = ""
        claude_msgs = []
        for m in messages:
            role = m.get("role", "user")
            content = m.get("content", "")
            if role == "system":
                system_prompt += f"{content}\n"
            elif role in ("user", "assistant"):
                claude_msgs.append({"role": role, "content": content or ""})
            elif role == "tool":
                claude_msgs.append({
                    "role": "user",
                    "content": f"[Tool Result: {m.get('name')}]: {content}"
                })
        return system_prompt.strip(), claude_msgs

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
                content=f"[Anthropic Claude ({target_model})] Ready. Set your ANTHROPIC_API_KEY in Settings to enable live completions.",
                model=target_model
            )

        system_prompt, formatted_messages = self._convert_messages(messages)
        payload: Dict[str, Any] = {
            "model": target_model,
            "messages": formatted_messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        if system_prompt:
            payload["system"] = system_prompt

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{self._base_url}/messages",
                headers={
                    "x-api-key": self._api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                },
                json=payload
            )
            resp.raise_for_status()
            data = resp.json()
            content_blocks = data.get("content", [])
            full_text = "".join(b.get("text", "") for b in content_blocks if b.get("type") == "text")
            return ChatCompletionResult(
                content=full_text,
                model=data.get("model", target_model),
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
            msg = f"[Anthropic Claude ({target_model})] Ready. Enter your API key in Settings."
            for w in msg.split(" "):
                yield w + " "
            return

        system_prompt, formatted_messages = self._convert_messages(messages)
        payload = {
            "model": target_model,
            "messages": formatted_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True
        }
        if system_prompt:
            payload["system"] = system_prompt

        async with httpx.AsyncClient(timeout=90.0) as client:
            async with client.stream(
                "POST",
                f"{self._base_url}/messages",
                headers={
                    "x-api-key": self._api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                },
                json=payload
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    line = line.strip()
                    if line.startswith("data: "):
                        data_str = line[6:]
                        try:
                            chunk = json.loads(data_str)
                            if chunk.get("type") == "content_block_delta":
                                delta = chunk.get("delta", {})
                                if delta.get("type") == "text_delta":
                                    yield delta.get("text", "")
                        except Exception:
                            pass

    async def analyze_image(
        self,
        image_base64: str,
        prompt: str,
        model: Optional[str] = None
    ) -> str:
        target_model = model or self._default_model
        raw_b64 = image_base64.split(",", 1)[-1] if "," in image_base64 else image_base64
        media_type = "image/png"

        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": raw_b64
                        }
                    },
                    {"type": "text", "text": prompt}
                ]
            }
        ]
        res = await self.chat_completion(messages=messages, model=target_model)
        return res.content
