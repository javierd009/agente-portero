"""
Audio Transcription Service
Transcribes audio messages using OpenAI Whisper
Supports Spanish and English (auto-detection)
"""
import io
import structlog
from openai import AsyncOpenAI
from typing import Optional

from config import settings

logger = structlog.get_logger()

# OpenAI client for Whisper (requires direct OpenAI key, not OpenRouter)
# Uses OPENAI_WHISPER_KEY if available, falls back to OPENAI_API_KEY
whisper_api_key = settings.OPENAI_WHISPER_KEY or settings.OPENAI_API_KEY
client = AsyncOpenAI(
    api_key=whisper_api_key,
    base_url="https://api.openai.com/v1"  # Direct OpenAI for Whisper
)


async def transcribe_audio(
    audio_bytes: bytes,
    language_hint: Optional[str] = None
) -> Optional[str]:
    """
    Transcribe audio to text using OpenAI Whisper

    Args:
        audio_bytes: Raw audio bytes (supports ogg, mp3, wav, m4a, webm)
        language_hint: Optional language hint ("es" for Spanish, "en" for English)
                      If not provided, Whisper auto-detects

    Returns:
        Transcribed text or None if transcription fails
    """
    try:
        # Create file-like object
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = "audio.ogg"  # WhatsApp typically sends ogg/opus

        # Call Whisper API
        params = {
            "model": "whisper-1",
            "file": audio_file,
            "response_format": "text"
        }

        # Add language hint if provided
        if language_hint:
            params["language"] = language_hint

        transcript = await client.audio.transcriptions.create(**params)

        logger.info(
            "audio_transcribed",
            length_bytes=len(audio_bytes),
            transcript_preview=transcript[:50] if transcript else None
        )

        return transcript.strip() if transcript else None

    except Exception as e:
        logger.error("transcription_failed", error=str(e))
        return None


async def detect_language_from_text(text: str) -> str:
    """
    Simple language detection based on common words

    Returns: "es" for Spanish, "en" for English
    """
    spanish_indicators = [
        "hola", "buenos", "dias", "tardes", "noches", "gracias",
        "por favor", "quiero", "necesito", "puedo", "donde", "como",
        "vengo", "visitar", "casa", "unidad", "estoy", "soy"
    ]

    text_lower = text.lower()

    spanish_count = sum(1 for word in spanish_indicators if word in text_lower)

    return "es" if spanish_count >= 2 else "en"
