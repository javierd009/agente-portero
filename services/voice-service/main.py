"""
Agente Portero - Voice Service
SIP ↔ OpenAI Realtime API Bridge

Handles incoming calls from Asterisk via ARI,
connects to OpenAI Realtime for AI conversation,
and integrates with backend for authorization decisions.
"""
import asyncio
import logging
import signal
from contextlib import asynccontextmanager

from config import get_settings
from ari_handler import ARIHandler
from audio_bridge import AudioSocketBridge

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if get_settings().debug else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class VoiceService:
    def __init__(self):
        self.settings = get_settings()
        self.audio_bridge = AudioSocketBridge(
            host=self.settings.audio_bridge_host,
            port=self.settings.audio_bridge_port
        )
        self.ari_handler = ARIHandler(self.settings, self.audio_bridge)
        self.running = False

    async def start(self):
        """Start the voice service"""
        logger.info("Starting Agente Portero Voice Service...")
        self.running = True

        try:
            # Start the AudioSocket bridge first
            await self.audio_bridge.start()
            logger.info(f"AudioSocket bridge listening on port {self.settings.audio_bridge_port}")

            # Then connect to Asterisk ARI
            await self.ari_handler.connect()
            logger.info("Connected to Asterisk ARI")

            # Keep running until stopped
            while self.running:
                await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"Voice service error: {e}")
            raise
        finally:
            await self.stop()

    async def stop(self):
        """Stop the voice service"""
        logger.info("Stopping Voice Service...")
        self.running = False
        await self.ari_handler.disconnect()
        await self.audio_bridge.stop()


async def main():
    service = VoiceService()

    # Handle shutdown signals
    loop = asyncio.get_event_loop()

    def shutdown_handler():
        logger.info("Shutdown signal received")
        asyncio.create_task(service.stop())

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, shutdown_handler)

    await service.start()


if __name__ == "__main__":
    asyncio.run(main())
