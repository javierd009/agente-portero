"""Voice Service Configuration"""
import os
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Asterisk ARI
    asterisk_ari_url: str = "http://localhost:8088/ari"
    asterisk_ari_user: str = "asterisk"
    asterisk_ari_password: str = "asterisk"
    asterisk_ari_app: str = "agente-portero"

    # OpenAI
    openai_api_key: str = ""
    openai_realtime_model: str = "gpt-4o-realtime-preview-2024-12-17"
    openai_realtime_url: str = "wss://api.openai.com/v1/realtime"

    # Backend
    backend_api_url: str = "http://localhost:8000"

    # Voice
    default_voice: str = "alloy"
    default_language: str = "es-MX"

    # Debug
    debug: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
