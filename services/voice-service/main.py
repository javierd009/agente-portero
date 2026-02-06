"""
Agente Portero - Voice Service
SIP ↔ OpenAI Realtime API Bridge

Handles incoming calls from Asterisk via AudioSocket,
connects to OpenAI Realtime for AI conversation,
and integrates with backend for authorization decisions.
"""
import asyncio
import logging
import signal
from aiohttp import web

from config import get_settings
from audio_bridge import AudioSocketBridge
from call_session import CallSession

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if get_settings().debug else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class VoiceService:
    """Voice service that handles calls via AudioSocket and OpenAI Realtime"""

    def __init__(self):
        self.settings = get_settings()
        self.audio_bridge = AudioSocketBridge(
            host=self.settings.audio_bridge_host,
            port=self.settings.audio_bridge_port
        )
        self.running = False
        self.http_app = None
        self.http_runner = None
        self.active_sessions: dict[str, CallSession] = {}

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
            "active_calls": len(self.active_sessions)
        })

    async def _on_new_call(self, channel_id: str):
        """Called when a new AudioSocket connection is established"""
        logger.info(f"New call received: {channel_id}")

        # Create a new call session
        session = CallSession(
            channel_id=channel_id,
            caller_id="intercom",
            settings=self.settings,
            ari_handler=None,  # No ARI needed with direct AudioSocket
            audio_bridge=self.audio_bridge,
            tenant_id="sitnova",
            guard_extension="1002"
        )

        self.active_sessions[channel_id] = session

        # Start the session (connects to OpenAI Realtime)
        asyncio.create_task(self._run_session(channel_id, session))

    async def _run_session(self, channel_id: str, session: CallSession):
        """Run a call session"""
        try:
            await session.start()
        except Exception as e:
            logger.error(f"Session error for {channel_id}: {e}")
        finally:
            if channel_id in self.active_sessions:
                del self.active_sessions[channel_id]
            logger.info(f"Session ended for {channel_id}")

    async def start(self):
        """Start the voice service"""
        logger.info("Starting Agente Portero Voice Service...")
        self.running = True

        try:
            # Start HTTP server for health checks
            self.http_app = self._create_http_app()
            self.http_runner = web.AppRunner(self.http_app)
            await self.http_runner.setup()
            http_site = web.TCPSite(self.http_runner, "0.0.0.0", 8091)
            await http_site.start()
            logger.info("HTTP health server listening on port 8091")

            # Start the AudioSocket bridge with callback for new calls
            await self.audio_bridge.start(on_new_session=self._on_new_call)
            logger.info(f"AudioSocket bridge listening on port {self.settings.audio_bridge_port}")

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

        # Stop all active sessions
        for session in list(self.active_sessions.values()):
            await session.stop()
        self.active_sessions.clear()

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
