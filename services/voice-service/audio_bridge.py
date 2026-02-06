"""
Audio Bridge - Handles bidirectional audio streaming between Asterisk and OpenAI
Uses Asterisk AudioSocket for bidirectional audio streaming
"""
import asyncio
import logging
import struct
import uuid
from typing import Optional, Callable, Dict
from dataclasses import dataclass
import numpy as np
from scipy import signal

logger = logging.getLogger(__name__)

# Audio format constants
# AudioSocket ALWAYS uses 8kHz regardless of channel format settings
# See: https://docs.asterisk.org/Configuration/Channel-Drivers/AudioSocket/
ASTERISK_SAMPLE_RATE = 8000   # AudioSocket: signed linear 16-bit 8kHz mono PCM
OPENAI_SAMPLE_RATE = 24000    # OpenAI Realtime API: 24kHz
BYTES_PER_SAMPLE = 2          # 16-bit signed PCM
CHUNK_MS = 20                 # 20ms chunks
BYTES_PER_CHUNK = int(ASTERISK_SAMPLE_RATE * (CHUNK_MS / 1000.0) * BYTES_PER_SAMPLE)


def resample_audio(audio_data: bytes, from_rate: int, to_rate: int) -> bytes:
    """
    High-quality audio resampling using scipy's polyphase filter.
    Properly handles anti-aliasing for downsampling.
    """
    if from_rate == to_rate:
        return audio_data

    if len(audio_data) < 2:
        return audio_data

    # PCM16 little-endian (standard for most systems)
    audio_array = np.frombuffer(audio_data, dtype='<i2').astype(np.float64)

    if len(audio_array) == 0:
        return audio_data

    # Find the GCD to simplify the ratio
    from math import gcd
    g = gcd(from_rate, to_rate)
    up = to_rate // g
    down = from_rate // g

    # Use scipy's polyphase resampler - high quality with proper anti-aliasing
    resampled = signal.resample_poly(audio_array, up, down)

    # Clip and convert back to int16 little-endian
    resampled = np.clip(resampled, -32768, 32767).astype('<i2')

    return resampled.tobytes()


@dataclass
class AudioSession:
    """Represents an active audio session"""
    channel_id: str
    reader: Optional[asyncio.StreamReader] = None
    writer: Optional[asyncio.StreamWriter] = None
    on_audio_received: Optional[Callable[[bytes], None]] = None
    running: bool = False


class AudioBridge:
    """
    Handles audio streaming between Asterisk External Media and the application.

    Asterisk External Media sends RTP-like UDP packets.
    This bridge receives those packets and forwards PCM audio to OpenAI.
    """

    def __init__(self, host: str = "0.0.0.0", port: int = 8089):
        self.host = host
        self.port = port
        self.sessions: Dict[str, AudioSession] = {}
        self.server: Optional[asyncio.AbstractServer] = None
        self.udp_transport: Optional[asyncio.DatagramTransport] = None
        self.running = False

    async def start(self):
        """Start the audio bridge server"""
        self.running = True

        # Start UDP server for RTP-like audio from Asterisk External Media
        loop = asyncio.get_event_loop()
        self.udp_transport, _ = await loop.create_datagram_endpoint(
            lambda: AudioUDPProtocol(self),
            local_addr=(self.host, self.port)
        )

        logger.info(f"Audio bridge listening on UDP {self.host}:{self.port}")

    async def stop(self):
        """Stop the audio bridge"""
        self.running = False

        # Close all sessions
        for session in list(self.sessions.values()):
            await self.close_session(session.channel_id)

        # Close UDP transport
        if self.udp_transport:
            self.udp_transport.close()

        logger.info("Audio bridge stopped")

    def create_session(
        self,
        channel_id: str,
        on_audio_received: Callable[[bytes], None]
    ) -> AudioSession:
        """Create a new audio session for a channel"""
        session = AudioSession(
            channel_id=channel_id,
            on_audio_received=on_audio_received,
            running=True
        )
        self.sessions[channel_id] = session
        logger.info(f"Audio session created for channel {channel_id}")
        return session

    async def close_session(self, channel_id: str):
        """Close an audio session"""
        if channel_id in self.sessions:
            session = self.sessions.pop(channel_id)
            session.running = False
            if session.writer:
                session.writer.close()
                try:
                    await session.writer.wait_closed()
                except Exception:
                    pass
            logger.info(f"Audio session closed for channel {channel_id}")

    def receive_audio(self, channel_id: str, audio_data: bytes):
        """Called when audio is received from Asterisk"""
        if channel_id in self.sessions:
            session = self.sessions[channel_id]
            if session.on_audio_received and session.running:
                session.on_audio_received(audio_data)

    async def send_audio(self, channel_id: str, audio_data: bytes):
        """Send audio back to Asterisk"""
        if channel_id in self.sessions:
            session = self.sessions[channel_id]
            if session.writer and session.running:
                try:
                    session.writer.write(audio_data)
                    await session.writer.drain()
                except Exception as e:
                    logger.error(f"Error sending audio to channel {channel_id}: {e}")


class AudioUDPProtocol(asyncio.DatagramProtocol):
    """UDP Protocol handler for receiving audio from Asterisk External Media"""

    def __init__(self, bridge: AudioBridge):
        self.bridge = bridge
        self.channel_mapping: Dict[tuple, str] = {}  # Maps (host, port) to channel_id

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data: bytes, addr: tuple):
        """Handle incoming UDP packet from Asterisk"""
        # External Media sends raw PCM audio
        # First 12 bytes are typically RTP header, but External Media can send raw PCM

        if len(data) < 12:
            return

        # Try to extract channel ID from first packet or use address mapping
        channel_id = self.channel_mapping.get(addr)

        if channel_id:
            # Skip RTP header (12 bytes) if present, or process raw PCM
            audio_data = data[12:] if len(data) > 12 + BYTES_PER_CHUNK else data
            self.bridge.receive_audio(channel_id, audio_data)

    def register_channel(self, addr: tuple, channel_id: str):
        """Register a channel's address for audio routing"""
        self.channel_mapping[addr] = channel_id
        logger.debug(f"Registered audio source {addr} for channel {channel_id}")

    def error_received(self, exc):
        logger.error(f"UDP error: {exc}")


class AudioSocketBridge:
    """
    Alternative: TCP-based AudioSocket protocol for Asterisk.
    AudioSocket is simpler than External Media for bidirectional audio.

    Protocol:
    - First 3 bytes: message type (0x01 = UUID, 0x10 = audio, 0x00 = hangup)
    - Next 2 bytes: payload length (big-endian)
    - Remaining: payload
    """

    def __init__(self, host: str = "0.0.0.0", port: int = 8089):
        self.host = host
        self.port = port
        self.sessions: Dict[str, AudioSession] = {}
        self.server: Optional[asyncio.AbstractServer] = None
        self.running = False
        self.on_new_session: Optional[Callable[[str], None]] = None

    async def start(self, on_new_session: Optional[Callable[[str], None]] = None):
        """Start the AudioSocket server"""
        self.running = True
        self.on_new_session = on_new_session

        self.server = await asyncio.start_server(
            self._handle_connection,
            self.host,
            self.port
        )

        logger.info(f"AudioSocket bridge listening on TCP {self.host}:{self.port}")

    async def stop(self):
        """Stop the AudioSocket bridge"""
        self.running = False

        # Close all sessions
        for session in list(self.sessions.values()):
            await self.close_session(session.channel_id)

        # Close server
        if self.server:
            self.server.close()
            await self.server.wait_closed()

        logger.info("AudioSocket bridge stopped")

    async def _handle_connection(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter
    ):
        """Handle new AudioSocket connection from Asterisk"""
        channel_id = None

        try:
            # CRITICAL: Disable Nagle's algorithm for real-time audio
            # This prevents TCP from batching small packets together
            sock = writer.get_extra_info('socket')
            if sock:
                import socket
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                logger.debug("TCP_NODELAY enabled for AudioSocket connection")

            # First message should be UUID (channel ID)
            msg_type, payload = await self._read_message(reader)

            if msg_type != 0x01:  # UUID type
                logger.error(f"Expected UUID message, got type {msg_type}")
                return

            # AudioSocket sends 16-byte binary UUID
            # See: https://github.com/CyCoreSystems/audiosocket
            if len(payload) == 16:
                # Binary UUID format
                channel_id = str(uuid.UUID(bytes=payload))
            else:
                # Text UUID format (fallback)
                channel_id = payload.decode('utf-8').strip('\x00')
            logger.info(f"AudioSocket connection from channel {channel_id}")

            # Create or update session
            if channel_id in self.sessions:
                session = self.sessions[channel_id]
                session.reader = reader
                session.writer = writer
                session.running = True
            else:
                session = AudioSession(
                    channel_id=channel_id,
                    reader=reader,
                    writer=writer,
                    running=True
                )
                self.sessions[channel_id] = session

            # Notify about new session (async or sync callback)
            if self.on_new_session:
                if asyncio.iscoroutinefunction(self.on_new_session):
                    await self.on_new_session(channel_id)
                else:
                    self.on_new_session(channel_id)

            # Read audio loop
            audio_chunk_count = 0
            while session.running and self.running:
                try:
                    msg_type, payload = await asyncio.wait_for(
                        self._read_message(reader),
                        timeout=30.0
                    )

                    if msg_type == 0x10:  # Audio
                        audio_chunk_count += 1
                        # Log first few chunks for debugging
                        if audio_chunk_count <= 3:
                            logger.info(f"Audio chunk #{audio_chunk_count}: {len(payload)} bytes")
                        if session.on_audio_received:
                            session.on_audio_received(payload)
                    elif msg_type == 0x00:  # Hangup
                        logger.info(f"Hangup received for channel {channel_id}")
                        break
                    elif msg_type == 0x02:  # Error from Asterisk
                        error_code = payload[0] if payload else 0
                        logger.error(f"Asterisk error code: {error_code}")
                        break

                except asyncio.TimeoutError:
                    # Send silence to keep connection alive
                    continue

        except asyncio.IncompleteReadError:
            logger.debug(f"Connection closed for channel {channel_id}")
        except Exception as e:
            logger.error(f"AudioSocket error for channel {channel_id}: {e}")
        finally:
            if channel_id:
                await self.close_session(channel_id)
            writer.close()

    async def _read_message(
        self,
        reader: asyncio.StreamReader
    ) -> tuple[int, bytes]:
        """Read an AudioSocket message"""
        # Read header: 1 byte type + 2 bytes length
        header = await reader.readexactly(3)
        msg_type = header[0]
        length = struct.unpack('>H', header[1:3])[0]

        # Read payload
        payload = await reader.readexactly(length) if length > 0 else b''

        return msg_type, payload

    async def send_audio(self, channel_id: str, audio_data: bytes):
        """Send audio to Asterisk via AudioSocket"""
        if channel_id not in self.sessions:
            logger.warning(f"send_audio: channel {channel_id} not in sessions")
            return

        session = self.sessions[channel_id]
        if not session.writer or not session.running:
            logger.warning(f"send_audio: session not ready (writer={session.writer is not None}, running={session.running})")
            return

        try:
            # AudioSocket message: type (1 byte) + length (2 bytes) + payload
            header = struct.pack('>BH', 0x10, len(audio_data))
            session.writer.write(header + audio_data)
            await session.writer.drain()
            # Log first send
            if not hasattr(self, '_logged_first_send'):
                logger.info(f"First audio sent to Asterisk: {len(audio_data)} bytes")
                self._logged_first_send = True
        except Exception as e:
            logger.error(f"Error sending audio to {channel_id}: {e}")

    def set_audio_callback(
        self,
        channel_id: str,
        callback: Callable[[bytes], None]
    ):
        """Set the callback for received audio"""
        if channel_id in self.sessions:
            self.sessions[channel_id].on_audio_received = callback

    async def close_session(self, channel_id: str):
        """Close an audio session"""
        if channel_id in self.sessions:
            session = self.sessions.pop(channel_id)
            session.running = False
            logger.info(f"AudioSocket session closed for channel {channel_id}")
