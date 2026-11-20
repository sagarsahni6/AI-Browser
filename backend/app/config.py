import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

_curr = Path(__file__).resolve().parent
_candidates = [
    Path.cwd() / ".env",
    _curr.parent.parent / ".env",
    _curr.parent / ".env",
    Path.cwd() / "backend" / ".env",
]
_env_file = next((str(p) for p in _candidates if p.exists()), ".env")

class Settings(BaseSettings):
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    DEBUG: bool = False
    SECRET_TOKEN: str = "local-dev-secret-token"

    # AI Provider Settings (NVIDIA NIM)
    NVIDIA_BASE_URL: str = "https://integrate.api.nvidia.com/v1"
    NVIDIA_API_KEY: Optional[str] = None
    NVIDIA_MODEL: str = "nvidia/nemotron-3.5-lightning-30b-a3b"
    NVIDIA_VISION_MODEL: str = "nvidia/nemotron-3.5-super-vl-120b-a12b"
    NVIDIA_REASONING_MODEL: str = "mistralai/mistral-large-4-1t-a52b"

    # OpenAI Fallback
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./ai_browser.db"

    model_config = SettingsConfigDict(
        env_file=_env_file,
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
