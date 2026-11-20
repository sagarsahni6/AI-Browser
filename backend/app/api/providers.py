from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List, Optional
import httpx
from backend.app.config import settings
from backend.app.dependencies import verify_local_token
from backend.app.ai.registry import provider_registry

router = APIRouter(prefix="/providers", tags=["providers"], dependencies=[Depends(verify_local_token)])

class ProviderInfo(BaseModel):
    id: str
    name: str
    is_primary: bool
    configured: bool
    base_url: str
    default_model: str

class TestProviderRequest(BaseModel):
    provider_id: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None

class TestProviderResponse(BaseModel):
    success: bool
    message: str
    available_models: List[str]

@router.get("", response_model=List[ProviderInfo])
async def list_providers():
    return [
        ProviderInfo(
            id="nvidia_nim",
            name="NVIDIA NIM",
            is_primary=True,
            configured=bool(settings.NVIDIA_API_KEY),
            base_url=settings.NVIDIA_BASE_URL,
            default_model=settings.NVIDIA_MODEL
        ),
        ProviderInfo(
            id="openai_compatible",
            name="OpenAI Compatible",
            is_primary=False,
            configured=bool(settings.OPENAI_API_KEY),
            base_url=settings.OPENAI_BASE_URL,
            default_model=settings.OPENAI_MODEL
        ),
        ProviderInfo(
            id="anthropic",
            name="Anthropic Claude",
            is_primary=False,
            configured=bool(getattr(settings, "ANTHROPIC_API_KEY", None)),
            base_url="https://api.anthropic.com/v1",
            default_model=getattr(settings, "ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")
        ),
        ProviderInfo(
            id="google_gemini",
            name="Google Gemini",
            is_primary=False,
            configured=bool(getattr(settings, "GOOGLE_API_KEY", None)),
            base_url="https://generativelanguage.googleapis.com/v1beta",
            default_model=getattr(settings, "GOOGLE_MODEL", "gemini-2.0-flash")
        ),
        ProviderInfo(
            id="groq",
            name="Groq (Ultra-Fast)",
            is_primary=False,
            configured=bool(getattr(settings, "GROQ_API_KEY", None)),
            base_url="https://api.groq.com/openai/v1",
            default_model=getattr(settings, "GROQ_MODEL", "llama-3.3-70b-versatile")
        ),
        ProviderInfo(
            id="ollama",
            name="Ollama (Local)",
            is_primary=False,
            configured=True, # Local doesn't need key
            base_url=getattr(settings, "OLLAMA_BASE_URL", "http://localhost:11434"),
            default_model=getattr(settings, "OLLAMA_MODEL", "llama3.2")
        )
    ]

@router.post("/test", response_model=TestProviderResponse)
async def test_provider(req: TestProviderRequest):
    provider = provider_registry.get(req.provider_id)
    if not provider:
        return TestProviderResponse(success=False, message="Unknown provider", available_models=[])

    try:
        is_ok = await provider.check_connection()
        models = await provider.list_models()
        if is_ok:
            return TestProviderResponse(
                success=True,
                message=f"Connected to {provider.name} successfully!",
                available_models=models
            )
        else:
            return TestProviderResponse(
                success=False,
                message=f"Could not connect to {provider.name}. Check your API key or endpoint.",
                available_models=models
            )
    except Exception as e:
        return TestProviderResponse(
            success=False,
            message=f"Connection test error: {str(e)}",
            available_models=[]
        )

@router.get("/models", response_model=List[str])
async def list_available_models(provider_id: Optional[str] = None):
    provider = provider_registry.get(provider_id)
    try:
        return await provider.list_models()
    except Exception:
        return [
            "nvidia/nemotron-3.5-lightning-30b-a3b",
            "meta/llama-3.3-70b-instruct",
            "gpt-4o",
            "claude-3-5-sonnet-20241022",
            "gemini-2.0-flash",
            "llama-3.3-70b-versatile",
            "llama3.2"
        ]
