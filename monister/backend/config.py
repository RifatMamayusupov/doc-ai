"""
Monister Configuration - Settings and environment variables.
"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load .env from project root
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Base directories
    base_dir: Path = Path(__file__).parent
    templates_dir: Path = base_dir / "templates"
    uploads_dir: Path = base_dir.parent / "uploads"
    data_dir: Path = base_dir.parent / "data"  # User files organized by username
    
    # JWT Settings
    jwt_secret: str = os.getenv("JWT_SECRET", "monister-super-secret-key-change-in-production")
    jwt_expire_minutes: int = int(os.getenv("JWT_EXPIRE_MINUTES", str(60 * 24)))  # 24 hours
    
    # API Keys (from root .env)
    google_api_key: str = os.getenv("GOOGLE_API_KEY", "")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    tavily_api_key: str = os.getenv("TAVILY_API_KEY", "")
    
    # Model settings
    default_model: str = "gemini-3-pro-preview"
    
    # Server settings
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8000"))
    debug: bool = os.getenv("DEBUG", "true").lower() == "true"
    
    class Config:
        env_prefix = "MONISTER_"
        case_sensitive = False
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Ensure directories exist
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        self.uploads_dir.mkdir(parents=True, exist_ok=True)


# Global settings instance
settings = Settings()


# Export
__all__ = ["settings"]
