"""Voice Service Configuration"""
import os
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Asterisk ARI (default to production)
    asterisk_ari_url: str = "http://integrateccr.ddns.net:8880/ari"
    asterisk_ari_user: str = "asterisk"
    asterisk_ari_password: str = "asterisk123"
    asterisk_ari_app: str = "agente-portero"

    # Audio Bridge (AudioSocket)
    audio_bridge_host: str = "0.0.0.0"
    audio_bridge_port: int = 8089
    audio_sample_rate: int = 8000   # AudioSocket ALWAYS uses 8kHz (slin)
    audio_chunk_ms: int = 20  # 20ms chunks = 320 bytes @ 8kHz
    noise_gate_threshold: int = 200  # RMS threshold for gating low-level noise (0 disables)
    playback_prebuffer_frames: int = 10  # Initial frames to buffer before playback
    output_audio_queue_maxsize: int = 1000  # 1000 chunks ~= 20s at 20ms

    # OpenAI
    openai_api_key: str = ""
    openai_realtime_model: str = "gpt-4o-realtime-preview-2024-12-17"
    openai_realtime_url: str = "wss://api.openai.com/v1/realtime"

    # VAD tuning (server-side)
    vad_threshold: float = 0.6
    vad_prefix_padding_ms: int = 300
    vad_silence_duration_ms: int = 800

    # Backend
    backend_api_url: str = "http://localhost:8000"

    # Voice - Options: alloy, shimmer, coral, sage, echo, ash, ballad, verse
    default_voice: str = "shimmer"  # Shimmer: clearer, good for Spanish
    default_language: str = "es-MX"

    # Debug
    debug: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
