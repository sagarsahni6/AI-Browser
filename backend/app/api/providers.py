from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List, Optional
import httpx
from backend.app.config import settings
from backend.app.dependencies import verify_local_token

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
        )
    ]

@router.post("/test", response_model=TestProviderResponse)
async def test_provider(req: TestProviderRequest):
    api_key = req.api_key or (settings.NVIDIA_API_KEY if req.provider_id == "nvidia_nim" else settings.OPENAI_API_KEY)
    base_url = req.base_url or (settings.NVIDIA_BASE_URL if req.provider_id == "nvidia_nim" else settings.OPENAI_BASE_URL)

    if not api_key:
        return TestProviderResponse(
            success=False,
            message=f"No API key provided for {req.provider_id}",
            available_models=[]
        )

    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            resp = await client.get(
                f"{base_url}/models",
                headers={"Authorization": f"Bearer {api_key}"}
            )
            if resp.status_code == 200:
                data = resp.json()
                models = [m.get("id") for m in data.get("data", []) if m.get("id")]
                return TestProviderResponse(
                    success=True,
                    message="Connection successful!",
                    available_models=models[:10]
                )
            else:
                return TestProviderResponse(
                    success=False,
                    message=f"HTTP {resp.status_code}: {resp.text[:200]}",
                    available_models=[]
                )
    except Exception as e:
        return TestProviderResponse(
            success=False,
            message=f"Connection error: {str(e)}",
            available_models=[]
        )

@router.get("/models", response_model=List[str])
async def list_available_models():
    return [
        "meta/llama-3.3-70b-instruct",
        "meta/llama-3.2-90b-vision-instruct",
        "meta/llama-3.1-8b-instruct",
        "gpt-4o",
        "gpt-4o-mini"
    ]
