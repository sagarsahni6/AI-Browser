from pydantic import BaseModel
from typing import Dict

class ModelCapabilities(BaseModel):
    model_id: str
    supports_chat: bool = True
    supports_streaming: bool = True
    supports_tools: bool = False
    supports_vision: bool = False
    context_window: int = 8192

KNOWN_CAPABILITIES: Dict[str, ModelCapabilities] = {
    # NVIDIA NIM models
    "meta/llama-3.3-70b-instruct": ModelCapabilities(
        model_id="meta/llama-3.3-70b-instruct",
        supports_chat=True,
        supports_streaming=True,
        supports_tools=True,
        supports_vision=False,
        context_window=128000
    ),
    "meta/llama-3.2-90b-vision-instruct": ModelCapabilities(
        model_id="meta/llama-3.2-90b-vision-instruct",
        supports_chat=True,
        supports_streaming=True,
        supports_tools=False,
        supports_vision=True,
        context_window=128000
    ),
    "meta/llama-3.1-8b-instruct": ModelCapabilities(
        model_id="meta/llama-3.1-8b-instruct",
        supports_chat=True,
        supports_streaming=True,
        supports_tools=True,
        supports_vision=False,
        context_window=128000
    ),
    # OpenAI models
    "gpt-4o": ModelCapabilities(
        model_id="gpt-4o",
        supports_chat=True,
        supports_streaming=True,
        supports_tools=True,
        supports_vision=True,
        context_window=128000
    ),
    "gpt-4o-mini": ModelCapabilities(
        model_id="gpt-4o-mini",
        supports_chat=True,
        supports_streaming=True,
        supports_tools=True,
        supports_vision=True,
        context_window=128000
    )
}

def get_model_capabilities(model_id: str) -> ModelCapabilities:
    if model_id in KNOWN_CAPABILITIES:
        return KNOWN_CAPABILITIES[model_id]

    # Heuristic for unknown models
    is_vision = "vision" in model_id.lower() or "4o" in model_id.lower()
    return ModelCapabilities(
        model_id=model_id,
        supports_chat=True,
        supports_streaming=True,
        supports_tools=True,
        supports_vision=is_vision,
        context_window=16384
    )
