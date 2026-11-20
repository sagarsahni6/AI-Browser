import json
import httpx
from typing import AsyncGenerator, Dict, List, Optional, Any
from backend.app.ai.providers.base import BaseAIProvider, ChatCompletionResult
from backend.app.ai.capabilities import ModelCapabilities
from backend.app.config import settings

class GoogleGeminiProvider(BaseAIProvider):
    def __init__(self, api_key: Optional[str] = None, default_model: Optional[str] = None):
        self._api_key = api_key or getattr(settings, "GOOGLE_API_KEY", None)
        self._default_model = default_model or getattr(settings, "GOOGLE_MODEL", "gemini-2.0-flash")
        self._base_url = "https://generativelanguage.googleapis.com/v1beta"

    @property
    def provider_id(self) -> str:
        return "google_gemini"

    @property
    def name(self) -> str:
        return "Google Gemini"

    def get_capabilities(self, model: str) -> ModelCapabilities:
        return ModelCapabilities(
            supports_text=True,
            supports_vision=True,
            supports_tools=True,
            supports_json=True,
            context_window=1000000
        )

    async def check_connection(self) -> bool:
        if not self._api_key:
            return False
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(
                    f"{self._base_url}/models?key={self._api_key}"
                )
                return res.status_code == 200
        except Exception:
            return False

    async def list_models(self) -> List[str]:
        if not self._api_key:
            return ["gemini-2.0-flash", "gemini-2.0-pro-exp", "gemini-1.5-pro"]
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                res = await client.get(f"{self._base_url}/models?key={self._api_key}")
                if res.status_code == 200:
                    data = res.json()
                    return [
                        m["name"].replace("models/", "")
                        for m in data.get("models", [])
                        if "generateContent" in m.get("supportedGenerationMethods", [])
                    ][:10]
        except Exception:
            pass
        return ["gemini-2.0-flash", "gemini-1.5-pro"]

    def _convert_messages(self, messages: List[Dict[str, Any]]):
        system_instruction = None
        contents = []
        for m in messages:
            role = m.get("role", "user")
            content = m.get("content", "")
            if role == "system":
                system_instruction = {"parts": [{"text": str(content)}]}
            elif role == "user":
                contents.append({"role": "user", "parts": [{"text": str(content)}]})
            elif role == "assistant":
                contents.append({"role": "model", "parts": [{"text": str(content)}]})
            elif role == "tool":
                contents.append({"role": "user", "parts": [{"text": f"[Tool Result]: {content}"}]})
        return system_instruction, contents

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
                content=f"[Google Gemini ({target_model})] Ready. Set your GOOGLE_API_KEY in Settings to enable live completions.",
                model=target_model
            )

        system_instruction, contents = self._convert_messages(messages)
        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens
            }
        }
        if system_instruction:
            payload["systemInstruction"] = system_instruction

        url = f"{self._base_url}/models/{target_model}:generateContent?key={self._api_key}"
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            candidates = data.get("candidates", [])
            text = ""
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                text = "".join(p.get("text", "") for p in parts)
            return ChatCompletionResult(
                content=text,
                model=target_model,
                usage=data.get("usageMetadata")
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
            msg = f"[Google Gemini ({target_model})] Ready. Set your API key in Settings."
            for w in msg.split(" "):
                yield w + " "
            return

        system_instruction, contents = self._convert_messages(messages)
        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens
            }
        }
        if system_instruction:
            payload["systemInstruction"] = system_instruction

        url = f"{self._base_url}/models/{target_model}:streamGenerateContent?alt=sse&key={self._api_key}"
        async with httpx.AsyncClient(timeout=90.0) as client:
            async with client.stream("POST", url, json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    line = line.strip()
                    if line.startswith("data: "):
                        data_str = line[6:]
                        try:
                            chunk = json.loads(data_str)
                            candidates = chunk.get("candidates", [])
                            if candidates:
                                parts = candidates[0].get("content", {}).get("parts", [])
                                for p in parts:
                                    t = p.get("text")
                                    if t:
                                        yield t
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

        url = f"{self._base_url}/models/{target_model}:generateContent?key={self._api_key}"
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt},
                        {
                            "inlineData": {
                                "mimeType": "image/png",
                                "data": raw_b64
                            }
                        }
                    ]
                }
            ]
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            candidates = data.get("candidates", [])
            text = ""
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                text = "".join(p.get("text", "") for p in parts)
            return text
