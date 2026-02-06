"""Vision Service Configuration"""
import os
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Hikvision Camera
    hikvision_host: str = "192.168.1.100"
    hikvision_port: int = 80
    hikvision_user: str = "admin"
    hikvision_password: str = ""

    # Backend
    backend_api_url: str = "http://localhost:8000"

    # Detection
    yolo_model: str = "yolov8n.pt"
    yolo_confidence: float = 0.5
    ocr_language: str = "es"

    # Service
    service_port: int = 8001
    debug: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
