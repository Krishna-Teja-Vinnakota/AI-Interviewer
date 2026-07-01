"""Configuration management for the application."""
import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # MongoDB Configuration
    MONGODB_URI: str
    MONGODB_DATABASE_NAME: str = "ai_interviewer"
    
    # Vertex AI Configuration
    VERTEX_AI_SERVICE_ACCOUNT_PATH: str
    VERTEX_AI_PROJECT_ID: Optional[str] = None
    VERTEX_AI_LOCATION: str = "us-central1"
    
    # Google Cloud TTS Configuration
    GOOGLE_TTS_CREDENTIALS_PATH: Optional[str] = None  # Can use same as Vertex AI
    
    # Deepgram Configuration
    DEEPGRAM_API_KEY: str
    
    # Bunny CDN Configuration
    BUNNY_STORAGE_ZONE: str
    BUNNY_API_KEY: str
    BUNNY_CDN_HOSTNAME: str
    BUNNY_STORAGE_REGION: str = "de"
    
    # SMTP Configuration (for sending emails)
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_TLS: bool = True
    
    # Application Configuration
    BASE_URL: str = "http://localhost:8000"
    TIMEZONE: str = "Asia/Kolkata"  # IST
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()


def get_vertex_ai_credentials() -> dict:
    """Load Vertex AI service account credentials from JSON file."""
    credentials_path = Path(settings.VERTEX_AI_SERVICE_ACCOUNT_PATH)
    if not credentials_path.exists():
        raise FileNotFoundError(
            f"Vertex AI service account file not found: {credentials_path}"
        )
    
    import json
    with open(credentials_path, 'r') as f:
        return json.load(f)


def get_google_tts_credentials() -> dict:
    """Load Google TTS credentials (can use same as Vertex AI)."""
    if settings.GOOGLE_TTS_CREDENTIALS_PATH:
        credentials_path = Path(settings.GOOGLE_TTS_CREDENTIALS_PATH)
    else:
        credentials_path = Path(settings.VERTEX_AI_SERVICE_ACCOUNT_PATH)
    
    if not credentials_path.exists():
        raise FileNotFoundError(
            f"Google TTS credentials file not found: {credentials_path}"
        )
    
    import json
    with open(credentials_path, 'r') as f:
        return json.load(f)
