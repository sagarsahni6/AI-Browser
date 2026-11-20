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

    # Anthropic Claude
    ANTHROPIC_API_KEY: Optional[str] = None
    ANTHROPIC_MODEL: str = "claude-3-5-sonnet-20241022"

    # Google Gemini
    GOOGLE_API_KEY: Optional[str] = None
    GOOGLE_MODEL: str = "gemini-2.0-flash"

    # Groq (Ultra-Fast)
    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    # Ollama (Local)
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2"

    # Default Active Provider
    DEFAULT_PROVIDER: str = "nvidia_nim"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./ai_browser.db"

    model_config = SettingsConfigDict(
        env_file=_env_file,
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
