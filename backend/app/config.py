from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    DEBUG: bool = False
    SECRET_TOKEN: str = "local-dev-secret-token"

    # AI Provider Settings (NVIDIA NIM)
    NVIDIA_BASE_URL: str = "https://integrate.api.nvidia.com/v1"
    NVIDIA_API_KEY: Optional[str] = None
    NVIDIA_MODEL: str = "minimaxai/minimax-m3.1-flash"
    NVIDIA_VISION_MODEL: str = "nvidia/nemotron-3.5-super-vl-120b-a12b"

    # OpenAI Fallback
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./ai_browser.db"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
