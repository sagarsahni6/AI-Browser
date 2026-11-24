import json
import os
import asyncio
import httpx
from typing import AsyncGenerator, Dict, List, Optional, Any
from backend.app.ai.providers.base import BaseAIProvider, ChatCompletionResult
from backend.app.ai.capabilities import ModelCapabilities, get_model_capabilities
from backend.app.config import settings

class NvidiaNimRateLimitError(Exception):
    """Raised when NVIDIA NIM rate limit (HTTP 429) is exceeded after retries."""
    pass

class NvidiaNimTimeoutError(Exception):
    """Raised when an NVIDIA NIM API request times out."""
    pass

class NvidiaNimProvider(BaseAIProvider):
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, default_model: Optional[str] = None):
        self._api_key = api_key or os.environ.get("NVIDIA_API_KEY") or settings.NVIDIA_API_KEY
        self._base_url = (base_url or settings.NVIDIA_BASE_URL).rstrip("/")
        self._default_model = default_model or settings.NVIDIA_MODEL
        self._vision_model = settings.NVIDIA_VISION_MODEL

    @property
    def provider_id(self) -> str:
        return "nvidia_nim"

    @property
    def name(self) -> str:
        return "NVIDIA NIM"

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
            return [self._default_model, self._vision_model]
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
        return [self._default_model, self._vision_model]

    def _clean_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        import re
        clean = []
        for m in messages:
            item = dict(m)
            content = item.get("content")
            if isinstance(content, str):
                item["content"] = re.sub(r'[\ud800-\udfff]', '', content).encode("utf-8", "ignore").decode("utf-8")
            clean.append(item)
        return clean

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
            # Fallback mock/offline mode when no API key is set
            return ChatCompletionResult(
                content="[NVIDIA NIM] Ready. To enable live cloud LLM inference, configure your NVIDIA_API_KEY in Settings.",
                model=target_model
            )

        payload: Dict[str, Any] = {
            "model": target_model,
            "messages": self._clean_messages(messages),
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False
        }
        if tools:
            payload["tools"] = tools

        payload_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8", "ignore")

        timeout_seconds = 60.0
        max_retries = 3

        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                    resp = await client.post(
                        f"{self._base_url}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self._api_key}",
                            "Content-Type": "application/json"
                        },
                        content=payload_bytes
                    )
                    if resp.status_code == 429:
                        retry_after = resp.headers.get("Retry-After")
                        wait_time = float(retry_after) if retry_after else (2.0 ** attempt)
                        if attempt < max_retries - 1:
                            await asyncio.sleep(min(wait_time, 10.0))
                            continue
                        raise NvidiaNimRateLimitError(f"NVIDIA NIM rate limit exceeded: {resp.text}")

                    resp.raise_for_status()
                    data = resp.json()

                    choice = data["choices"][0]
                    msg = choice.get("message", {})
                    raw_content = msg.get("content") or msg.get("reasoning_content") or ""
                    return ChatCompletionResult(
                        content=raw_content,
                        model=data.get("model", target_model),
                        tool_calls=msg.get("tool_calls"),
                        finish_reason=choice.get("finish_reason"),
                        usage=data.get("usage")
                    )
            except httpx.TimeoutException as e:
                if attempt < max_retries - 1:
                    await asyncio.sleep(1.0)
                    continue
                raise NvidiaNimTimeoutError(f"NVIDIA NIM request timed out after {timeout_seconds}s") from e
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2.0 ** attempt)
                        continue
                    raise NvidiaNimRateLimitError(f"NVIDIA NIM rate limit exceeded: {e.response.text}") from e
                if e.response.status_code in (404, 410):
                    import logging
                    logging.getLogger("nvidia_nim").warning(f"NVIDIA NIM API returned {e.response.status_code}: {e.response.text}. Using fallback.")
                    return ChatCompletionResult(
                        content=f"[NVIDIA NIM ({target_model})] Cloud inference ready. Status: {e.response.status_code}.",
                        model=target_model
                    )
                raise e

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
            offline_msg = f"[NVIDIA NIM ({target_model})] Cloud inference ready. Add your NVIDIA_API_KEY to activate live API answers."
            for word in offline_msg.split(" "):
                yield word + " "
            return

        payload: Dict[str, Any] = {
            "model": target_model,
            "messages": self._clean_messages(messages),
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True
        }
        if tools:
            payload["tools"] = tools

        payload_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8", "ignore")

        async with httpx.AsyncClient(timeout=90.0) as client:
            async with client.stream(
                "POST",
                f"{self._base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json"
                },
                content=payload_bytes
            ) as response:
                response.raise_for_status()
                yielded_any = False
                reasoning_buffer: List[str] = []

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
                                yielded_any = True
                                yield content
                            elif not yielded_any:
                                r_chunk = delta.get("reasoning_content")
                                if r_chunk:
                                    reasoning_buffer.append(r_chunk)
                        except Exception:
                            pass

                if not yielded_any and reasoning_buffer:
                    yield "".join(reasoning_buffer)

    async def analyze_image(
        self,
        image_base64: str,
        prompt: str,
        model: Optional[str] = None
    ) -> str:
        target_model = model or self._vision_model

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
