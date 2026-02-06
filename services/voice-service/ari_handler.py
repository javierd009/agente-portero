"""
Asterisk ARI Handler
Manages WebSocket connection to Asterisk and handles call events
"""
import asyncio
import json
import logging
import base64
from typing import Dict, Optional, TYPE_CHECKING
import aiohttp
import websockets

from config import Settings
from call_session import CallSession

if TYPE_CHECKING:
    from audio_bridge import AudioSocketBridge

logger = logging.getLogger(__name__)


class ARIHandler:
    """Handles Asterisk REST Interface (ARI) connection and events"""

    def __init__(self, settings: Settings, audio_bridge: Optional["AudioSocketBridge"] = None):
        self.settings = settings
        self.audio_bridge = audio_bridge
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.http_session: Optional[aiohttp.ClientSession] = None
        self.active_sessions: Dict[str, CallSession] = {}
        self._reconnect_delay = 5
        self.connected = False

    @property
    def ws_url(self) -> str:
        """Build ARI WebSocket URL"""
        base = self.settings.asterisk_ari_url.replace("http://", "ws://").replace("https://", "wss://")
        return f"{base}/events?app={self.settings.asterisk_ari_app}&api_key={self.settings.asterisk_ari_user}:{self.settings.asterisk_ari_password}"

    @property
    def api_url(self) -> str:
        """Base URL for ARI REST API"""
        return self.settings.asterisk_ari_url

    async def connect(self):
        """Connect to Asterisk ARI"""
        self.http_session = aiohttp.ClientSession(
            auth=aiohttp.BasicAuth(
                self.settings.asterisk_ari_user,
                self.settings.asterisk_ari_password
            )
        )

        await self._connect_websocket()

    async def _connect_websocket(self):
        """Establish WebSocket connection with reconnection logic"""
        while True:
            try:
                logger.info(f"Connecting to ARI WebSocket...")
                self.ws = await websockets.connect(self.ws_url)
                self.connected = True
                logger.info("ARI WebSocket connected")

                # Start listening for events
                await self._listen_events()

            except websockets.exceptions.ConnectionClosed:
                self.connected = False
                logger.warning("ARI WebSocket connection closed, reconnecting...")
            except Exception as e:
                self.connected = False
                logger.error(f"ARI WebSocket error: {e}")

            await asyncio.sleep(self._reconnect_delay)

    async def _listen_events(self):
        """Listen for ARI events"""
        async for message in self.ws:
            try:
                event = json.loads(message)
                await self._handle_event(event)
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON from ARI: {message}")
            except Exception as e:
                logger.error(f"Error handling ARI event: {e}")

    async def _handle_event(self, event: dict):
        """Handle ARI event"""
        event_type = event.get("type")
        logger.debug(f"ARI Event: {event_type}")

        if event_type == "StasisStart":
            await self._handle_stasis_start(event)
        elif event_type == "StasisEnd":
            await self._handle_stasis_end(event)
        elif event_type == "ChannelDtmfReceived":
            await self._handle_dtmf(event)
        elif event_type == "ChannelHangupRequest":
            await self._handle_hangup(event)

    async def _handle_stasis_start(self, event: dict):
        """Handle new incoming call"""
        channel = event.get("channel", {})
        channel_id = channel.get("id")
        caller_id = channel.get("caller", {}).get("number", "unknown")

        # Extract tenant_id from Stasis args or channel variables
        args = event.get("args", [])
        tenant_id = args[0] if args else "default"

        # Also check channel variables (set via Set(CHANNEL(tenant_id)=xxx))
        channel_vars = channel.get("channelvars", {})
        if "tenant_id" in channel_vars:
            tenant_id = channel_vars["tenant_id"]

        # Get guard extension for human-in-the-loop transfers
        guard_extension = channel_vars.get("guard_extension", "1002")

        logger.info(f"New call from {caller_id} on channel {channel_id} (tenant: {tenant_id})")

        # Answer the call
        await self._answer_channel(channel_id)

        # Create new call session with OpenAI
        session = CallSession(
            channel_id=channel_id,
            caller_id=caller_id,
            settings=self.settings,
            ari_handler=self,
            audio_bridge=self.audio_bridge,
            tenant_id=tenant_id,
            guard_extension=guard_extension
        )
        self.active_sessions[channel_id] = session

        # Start the AI session
        asyncio.create_task(session.start())

        # If using AudioSocket, Asterisk will connect to our bridge
        # If using External Media, start it now
        if not self.audio_bridge:
            await self._start_external_media_for_channel(channel_id)

    async def transfer_to_extension(self, channel_id: str, extension: str):
        """Transfer a call to another extension"""
        url = f"{self.api_url}/channels/{channel_id}/redirect"
        params = {"endpoint": f"PJSIP/{extension}"}
        async with self.http_session.post(url, params=params) as resp:
            if resp.status not in (200, 204):
                logger.error(f"Failed to transfer call: {await resp.text()}")
                return False
            logger.info(f"Call {channel_id} transferred to {extension}")
            return True

    async def _start_external_media_for_channel(self, channel_id: str):
        """Start external media for a channel (alternative to AudioSocket)"""
        try:
            media_uri = await self.start_external_media(channel_id)
            if media_uri:
                logger.info(f"External media started for {channel_id}: {media_uri}")
        except Exception as e:
            logger.error(f"Failed to start external media for {channel_id}: {e}")

    async def _handle_stasis_end(self, event: dict):
        """Handle call ended"""
        channel = event.get("channel", {})
        channel_id = channel.get("id")

        logger.info(f"Call ended on channel {channel_id}")

        if channel_id in self.active_sessions:
            session = self.active_sessions.pop(channel_id)
            await session.stop()

    async def _handle_dtmf(self, event: dict):
        """Handle DTMF input"""
        channel = event.get("channel", {})
        channel_id = channel.get("id")
        digit = event.get("digit")

        logger.debug(f"DTMF {digit} on channel {channel_id}")

        if channel_id in self.active_sessions:
            await self.active_sessions[channel_id].handle_dtmf(digit)

    async def _handle_hangup(self, event: dict):
        """Handle hangup request"""
        channel = event.get("channel", {})
        channel_id = channel.get("id")

        logger.info(f"Hangup requested on channel {channel_id}")

        if channel_id in self.active_sessions:
            session = self.active_sessions.pop(channel_id)
            await session.stop()

    async def _answer_channel(self, channel_id: str):
        """Answer a channel"""
        url = f"{self.api_url}/channels/{channel_id}/answer"
        async with self.http_session.post(url) as resp:
            if resp.status != 204:
                logger.error(f"Failed to answer channel: {await resp.text()}")

    async def play_audio(self, channel_id: str, audio_data: bytes):
        """Play audio to channel using external media"""
        # For OpenAI Realtime, we'll use external media streaming
        # This requires Asterisk configured with external media
        pass

    async def start_external_media(self, channel_id: str) -> str:
        """Start external media on channel, returns media URI"""
        url = f"{self.api_url}/channels/{channel_id}/externalMedia"
        params = {
            "app": self.settings.asterisk_ari_app,
            "external_host": "localhost:8089",  # Our media relay
            "format": "slin16"  # 16-bit signed linear PCM at 16kHz
        }
        async with self.http_session.post(url, params=params) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("local_address")
            else:
                logger.error(f"Failed to start external media: {await resp.text()}")
                return None

    async def hangup_channel(self, channel_id: str):
        """Hang up a channel"""
        url = f"{self.api_url}/channels/{channel_id}"
        async with self.http_session.delete(url) as resp:
            if resp.status not in (200, 204, 404):
                logger.error(f"Failed to hangup channel: {await resp.text()}")

    async def disconnect(self):
        """Disconnect from ARI"""
        self.connected = False
        # Stop all active sessions
        for session in list(self.active_sessions.values()):
            await session.stop()
        self.active_sessions.clear()

        # Close WebSocket
        if self.ws:
            await self.ws.close()

        # Close HTTP session
        if self.http_session:
            await self.http_session.close()
