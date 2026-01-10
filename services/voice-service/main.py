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
from aiohttp import web

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
        self.http_app = None
        self.http_runner = None

    def _create_http_app(self):
        """Create HTTP app for health checks"""
        app = web.Application()
        app.router.add_get("/health", self._health_handler)
        app.router.add_get("/", self._health_handler)
        return app

    async def _health_handler(self, request):
        """Health check endpoint"""
        return web.json_response({
            "status": "healthy",
            "service": "voice-service",
            "ari_connected": self.ari_handler.connected if hasattr(self.ari_handler, 'connected') else False,
            "active_calls": len(self.ari_handler.active_sessions) if hasattr(self.ari_handler, 'active_sessions') else 0
        })

    async def start(self):
        """Start the voice service"""
        logger.info("Starting Agente Portero Voice Service...")
        self.running = True

        try:
            # Start HTTP server for health checks
            self.http_app = self._create_http_app()
            self.http_runner = web.AppRunner(self.http_app)
            await self.http_runner.setup()
            http_site = web.TCPSite(self.http_runner, "0.0.0.0", 8001)
            await http_site.start()
            logger.info("HTTP health server listening on port 8001")

            # Start the AudioSocket bridge
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
        if self.http_runner:
            await self.http_runner.cleanup()


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
