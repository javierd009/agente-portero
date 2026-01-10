"""
WhatsApp Service Configuration
Handles bidirectional WhatsApp communication via Evolution API
"""
import os
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Service
    SERVICE_NAME: str = "whatsapp-service"
    PORT: int = 8002
    DEBUG: bool = True

    # Evolution API
    EVOLUTION_API_URL: str
    EVOLUTION_API_KEY: str
    EVOLUTION_INSTANCE: str
    EVOLUTION_WEBHOOK_URL: Optional[str] = None  # Our webhook URL (for Evolution to call)

    # Backend API
    BACKEND_API_URL: str = "http://localhost:8000"
    BACKEND_API_KEY: Optional[str] = None

    # OpenAI (for NLP intent parsing via OpenRouter)
    OPENAI_API_KEY: str  # OpenRouter key for chat/NLP
    OPENAI_MODEL: str = "gpt-4-turbo-preview"  # or "gpt-4o"

    # OpenAI Direct (for Whisper audio transcription)
    OPENAI_WHISPER_KEY: Optional[str] = None  # Direct OpenAI key for Whisper STT

    # Redis (session management)
    REDIS_URL: str = "redis://localhost:6379/0"
    SESSION_TTL: int = 3600  # 1 hour

    # Features
    ENABLE_VISITOR_AUTHORIZATION: bool = True
    ENABLE_REMOTE_GATE_OPEN: bool = True
    ENABLE_REPORTS: bool = True
    ENABLE_LOG_QUERIES: bool = True

    # Timeouts
    DEFAULT_AUTHORIZATION_TTL: int = 7200  # 2 hours
    MAX_AUTHORIZATION_TTL: int = 86400      # 24 hours

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
