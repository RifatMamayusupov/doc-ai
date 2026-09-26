"""Application configuration and settings."""

from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    
    # Database
    database_url: str = "sqlite+aiosqlite:///./docagent.db"
    
    # Redis
    redis_url: str = "redis://localhost:6379"
    
    # JWT Authentication
    jwt_secret: str = "super-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    
    # DeepAgents
    deepagents_model: str = "gemini-1.5-pro"
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    google_api_key: str | None = None
    tavily_api_key: str | None = None
    
    # File Storage
    upload_dir: Path = Path("./uploads")
    max_upload_size: int = 52428800  # 50MB
    
    # Extra Tools (dynamic code storage)
    extra_tools_dir: Path = Path("./extra_tools")
    
    # CORS
    cors_origins: list[str] = [
        "http://localhost:3000", 
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ]
    
    def ensure_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.extra_tools_dir.mkdir(parents=True, exist_ok=True)
        # Templates directory
        (self.upload_dir / "templates").mkdir(exist_ok=True)
        # User uploads
        (self.upload_dir / "users").mkdir(exist_ok=True)


settings = Settings()
