"""
Call Session - Manages a single call with OpenAI Realtime

Audio Format Strategy:
- AudioSocket ALWAYS uses signed linear 16-bit 8kHz mono PCM (slin)
- See: https://docs.asterisk.org/Configuration/Channel-Drivers/AudioSocket/
- OpenAI Realtime API uses pcm16 at 24kHz.
- We resample 8kHz ↔ 24kHz using scipy's polyphase filter.
"""
import asyncio
import audioop
import json
import logging
import base64
import time
from typing import Optional, TYPE_CHECKING, Callable
import websockets
import httpx
import numpy as np
from scipy import signal
from math import gcd

from config import Settings
from tools import AGENT_TOOLS, execute_tool

# Audio constants - CRITICAL: AudioSocket always uses 8kHz
DEFAULT_ASTERISK_SAMPLE_RATE = 8000   # AudioSocket: signed linear 16-bit 8kHz mono
DEFAULT_CHUNK_MS = 20
OPENAI_SAMPLE_RATE = 24000            # OpenAI pcm16: 24kHz
BYTES_PER_SAMPLE = 2                  # 16-bit signed PCM


class AudioResampler:
    """Simple resampler wrapper - scipy's polyphase filter handles continuity well."""

    def __init__(self, from_rate: int, to_rate: int):
        self.from_rate = from_rate
        self.to_rate = to_rate
        self.g = gcd(from_rate, to_rate)
        self.up = to_rate // self.g
        self.down = from_rate // self.g

    def resample(self, audio_data: bytes) -> bytes:
        """Resample audio using high-quality polyphase filter."""
        if self.from_rate == self.to_rate or len(audio_data) < 2:
            return audio_data

        audio_array = np.frombuffer(audio_data, dtype='<i2').astype(np.float64)
        if len(audio_array) == 0:
            return audio_data

        # High-quality polyphase resampling with anti-aliasing
        resampled = signal.resample_poly(audio_array, self.up, self.down)

        # Clip and convert back to int16
        resampled = np.clip(resampled, -32768, 32767).astype('<i2')
        return resampled.tobytes()

    def reset(self):
        """Reset state (no-op for stateless resampler)."""
        pass


def resample_audio(audio_data: bytes, from_rate: int, to_rate: int) -> bytes:
    """High-quality audio resampling using scipy's polyphase filter."""
    if from_rate == to_rate or len(audio_data) < 2:
        return audio_data

    # PCM16 little-endian
    audio_array = np.frombuffer(audio_data, dtype='<i2').astype(np.float64)
    if len(audio_array) == 0:
        return audio_data

    # Simplify ratio using GCD
    g = gcd(from_rate, to_rate)
    up = to_rate // g
    down = from_rate // g

    # High-quality polyphase resampling with anti-aliasing
    resampled = signal.resample_poly(audio_array, up, down)

    # Clip and convert back to int16 little-endian
    resampled = np.clip(resampled, -32768, 32767).astype('<i2')
    return resampled.tobytes()

if TYPE_CHECKING:
    from ari_handler import ARIHandler
    from audio_bridge import AudioSocketBridge

logger = logging.getLogger(__name__)


class CallSession:
    """Manages a single call session with OpenAI Realtime API"""

    def __init__(
        self,
        channel_id: str,
        caller_id: str,
        settings: Settings,
        ari_handler: "ARIHandler",
        audio_bridge: Optional["AudioSocketBridge"] = None,
        tenant_id: str = "default",
        guard_extension: str = "1002"
    ):
        self.channel_id = channel_id
        self.caller_id = caller_id
        self.settings = settings
        self.ari_handler = ari_handler
        self.audio_bridge = audio_bridge
        self.tenant_id = tenant_id
        self.guard_extension = guard_extension

        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.running = False
        self.conversation_id: Optional[str] = None
        # Input buffer for audio from Asterisk (20ms chunks, ~500ms buffer max)
        self.audio_buffer: asyncio.Queue = asyncio.Queue(maxsize=25)
        self.output_audio_queue_maxsize = max(100, int(settings.output_audio_queue_maxsize or 500))
        # Output buffer for audio to Asterisk (jitter buffer for smooth playback)
        # 1000 chunks ~= 20 seconds of audio at 20ms per chunk
        self.output_audio_queue: asyncio.Queue = asyncio.Queue(maxsize=self.output_audio_queue_maxsize)
        self.playback_task: Optional[asyncio.Task] = None
        self.chunks_dropped = 0  # Track dropped audio for debugging

        # Barge-in handling: track when AI is speaking
        self.ai_speaking = False
        self.last_ai_audio_time = 0.0
        self.playback_active = False
        self._detected_sample_rate = False

        self.asterisk_sample_rate = settings.audio_sample_rate or DEFAULT_ASTERISK_SAMPLE_RATE
        self.chunk_ms = settings.audio_chunk_ms or DEFAULT_CHUNK_MS
        self.chunk_bytes = int(self.asterisk_sample_rate * (self.chunk_ms / 1000.0) * BYTES_PER_SAMPLE)
        self.noise_gate_threshold = max(0, int(settings.noise_gate_threshold or 0))
        self.noise_gate_hits = 0
        self.playback_prebuffer_frames = max(1, int(settings.playback_prebuffer_frames or 1))

        # Playback statistics for drift detection
        self.playback_stats = {
            "chunks_sent": 0,
            "start_time": 0.0,
            "expected_duration": 0.0,
            "actual_duration": 0.0,
            "drift_corrections": 0
        }

        # Stateful resamplers for smooth audio transitions
        self.resampler_to_asterisk = AudioResampler(OPENAI_SAMPLE_RATE, self.asterisk_sample_rate)
        self.resampler_to_openai = AudioResampler(self.asterisk_sample_rate, OPENAI_SAMPLE_RATE)

        # Visitor info collected during conversation
        self.visitor_name: Optional[str] = None
        self.destination_unit: Optional[str] = None
        self.destination_resident: Optional[str] = None

    @property
    def openai_ws_url(self) -> str:
        return f"{self.settings.openai_realtime_url}?model={self.settings.openai_realtime_model}"

    def _get_system_prompt(self) -> str:
        """Get the system prompt for the AI agent"""
        return f"""Eres un agente de seguridad virtual profesional para el condominio "{self.tenant_id}".
Tu trabajo es atender a los visitantes que llegan a la puerta principal de manera eficiente y segura.

FLUJO PRINCIPAL DE CONVERSACIÓN:

1. SALUDO INICIAL:
   "Buenas [tardes/noches], bienvenido a [nombre del condominio]. Soy el sistema de seguridad. ¿En qué puedo ayudarle?"

2. IDENTIFICAR AL VISITANTE:
   - Pregunta: "¿Me podría dar su nombre, por favor?"
   - Guarda el nombre para usarlo durante la conversación

3. IDENTIFICAR EL DESTINO:
   El visitante puede decir:
   - Número de casa/departamento: "Voy a la casa 16" o "Al departamento 5B"
   - Nombre del residente: "Vengo con Carlos" o "Busco a la señora María"
   - Ambos: "Voy con Juan de la casa 8"

   Si solo da un dato, está bien. Usa find_resident para buscar.

4. VERIFICAR AUTORIZACIÓN:
   PRIMERO usa check_preauthorized_visitor para ver si hay una autorización previa.

   CASO A - VISITANTE PRE-AUTORIZADO:
   Si el residente ya reportó la visita previamente:
   - "Perfecto, [nombre del visitante]. El residente ya nos notificó de su visita. Le abro enseguida."
   - Usa open_gate para abrir
   - "Listo, puede pasar. Que tenga buen día."

   CASO B - VISITANTE NO PRE-AUTORIZADO:
   Si no hay autorización previa:
   - "Un momento por favor, [nombre]. Voy a comunicarme con el residente para confirmar."
   - Usa request_authorization para enviar WhatsApp al residente
   - Espera la respuesta (el sistema te notificará)

   Si el residente AUTORIZA:
   - "Listo [nombre], el residente ha autorizado su ingreso. Le abro la puerta."
   - Usa open_gate para abrir

   Si el residente NO AUTORIZA o no responde:
   - "Lo siento, no hemos podido confirmar su visita con el residente."
   - "¿Desea que lo comunique con un guardia de seguridad?"
   - Si dice sí, usa transfer_to_guard

5. CASOS ESPECIALES:

   DELIVERY/UBER/PAQUETERÍA:
   - Pregunta qué empresa es (Uber, Rappi, DHL, etc.)
   - Pregunta el destino (casa/depto o nombre)
   - Sigue el flujo normal de autorización

   EMERGENCIAS:
   - Si detectas una emergencia, transfiere inmediatamente a guardia
   - "Entiendo, lo comunico con seguridad de inmediato."
   - Usa transfer_to_guard

   RESIDENTE QUE OLVIDÓ LLAVE:
   - Verifica identidad preguntando datos
   - Usa verify_resident para confirmar
   - Si es válido, abre la puerta

REGLAS IMPORTANTES:
- Sé cortés pero eficiente, no hagas preguntas innecesarias
- Habla en español mexicano natural
- Usa el nombre del visitante cuando lo tengas
- NUNCA reveles información de los residentes (nombres, teléfonos, etc.)
- Si algo te parece sospechoso, transfiere a guardia humano
- Si el visitante se molesta o insiste, ofrece transferir a guardia

HERRAMIENTAS DISPONIBLES:
- find_resident: Buscar residente por nombre o número de unidad
- check_preauthorized_visitor: Verificar si hay autorización previa
- request_authorization: Enviar WhatsApp al residente pidiendo autorización
- open_gate: Abrir la puerta/portón de acceso
- transfer_to_guard: Transferir llamada a guardia humano (extensión {self.guard_extension})
- log_visit: Registrar la visita en bitácora
"""

    async def start(self):
        """Start the OpenAI Realtime session"""
        self.running = True

        try:
            # Connect to OpenAI Realtime
            logger.info(f"Connecting to OpenAI Realtime: {self.openai_ws_url}")

            if not self.settings.openai_api_key:
                logger.error("OpenAI API key is not configured!")
                raise ValueError("OPENAI_API_KEY is not set")

            headers = {
                "Authorization": f"Bearer {self.settings.openai_api_key}",
                "OpenAI-Beta": "realtime=v1"
            }

            self.ws = await websockets.connect(
                self.openai_ws_url,
                additional_headers=headers
            )
            logger.info(f"Connected to OpenAI Realtime for channel {self.channel_id}")

            # Configure the session
            await self._configure_session()

            # Start listening for OpenAI events, audio streaming, and playback
            listen_task = asyncio.create_task(self._listen_openai())
            stream_task = asyncio.create_task(self._stream_audio())
            self.playback_task = asyncio.create_task(self._playback_audio())

            # Wait for the listening task to complete (it runs until connection closes)
            # This keeps the session alive until the call ends
            await listen_task

            # Cancel streaming and playback tasks when listening ends
            stream_task.cancel()
            self.playback_task.cancel()
            try:
                await stream_task
            except asyncio.CancelledError:
                pass
            try:
                await self.playback_task
            except asyncio.CancelledError:
                pass

        except Exception as e:
            logger.error(f"Failed to start OpenAI session: {e}", exc_info=True)
            await self.stop()

    async def _configure_session(self):
        """Configure the OpenAI Realtime session"""
        # Use pcm16 at 24kHz - we handle resampling to/from the Asterisk sample rate
        config = {
            "type": "session.update",
            "session": {
                "modalities": ["text", "audio"],
                "instructions": self._get_system_prompt(),
                "voice": self.settings.default_voice,
                "input_audio_format": "pcm16",   # 24kHz 16-bit PCM
                "output_audio_format": "pcm16",  # 24kHz 16-bit PCM
                "input_audio_transcription": {
                    "model": "whisper-1"
                },
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": self.settings.vad_threshold,
                    "prefix_padding_ms": self.settings.vad_prefix_padding_ms,
                    "silence_duration_ms": self.settings.vad_silence_duration_ms
                },
                "tools": AGENT_TOOLS,
                "tool_choice": "auto"
            }
        }
        await self.ws.send(json.dumps(config))
        logger.info(
            "OpenAI session configured with pcm16 (24kHz) - resampling to/from Asterisk rate "
            f"(vad_threshold={self.settings.vad_threshold}, "
            f"vad_prefix_padding_ms={self.settings.vad_prefix_padding_ms}, "
            f"vad_silence_duration_ms={self.settings.vad_silence_duration_ms})"
        )

    async def _listen_openai(self):
        """Listen for events from OpenAI Realtime"""
        try:
            async for message in self.ws:
                if not self.running:
                    break

                event = json.loads(message)
                await self._handle_openai_event(event)

        except websockets.exceptions.ConnectionClosed:
            logger.info("OpenAI WebSocket closed")
        except Exception as e:
            logger.error(f"Error listening to OpenAI: {e}")
        finally:
            await self.stop()

    async def _handle_openai_event(self, event: dict):
        """Handle event from OpenAI Realtime"""
        event_type = event.get("type")

        if event_type == "session.created":
            logger.info(f"OpenAI session created: {event.get('session', {}).get('id')}")

        elif event_type == "response.audio.delta":
            # Audio chunk from OpenAI - send to Asterisk
            self.ai_speaking = True
            self.last_ai_audio_time = time.time()
            audio_b64 = event.get("delta")
            if audio_b64:
                audio_data = base64.b64decode(audio_b64)
                await self._send_audio_to_asterisk(audio_data)

        elif event_type == "response.audio.done":
            # AI finished outputting audio for this response
            self.ai_speaking = False
            logger.debug("AI audio output completed")

        elif event_type == "response.done":
            # AI finished entire response
            self.ai_speaking = False

        elif event_type == "input_audio_buffer.speech_started":
            # User started speaking - implement barge-in
            now = time.time()
            if self.playback_active or not self.output_audio_queue.empty():
                logger.debug(
                    "Ignoring barge-in while AI playback is active "
                    f"(queue={self.output_audio_queue.qsize()})"
                )
                return
            if self.ai_speaking or (now - self.last_ai_audio_time) < 0.5:
                logger.debug("Ignoring barge-in while AI recently spoke")
                return
            logger.debug("User speech started - clearing audio queue for barge-in")
            self._clear_output_queue()
            self.ai_speaking = False

        elif event_type == "response.audio_transcript.done":
            # AI finished speaking (transcript ready)
            transcript = event.get("transcript", "")
            logger.info(f"AI said: {transcript}")
            self.ai_speaking = False

        elif event_type == "conversation.item.input_audio_transcription.completed":
            # User speech transcribed
            transcript = event.get("transcript", "")
            logger.info(f"User said: {transcript}")

        elif event_type == "response.function_call_arguments.done":
            # Function call completed, execute it
            await self._handle_function_call(event)

        elif event_type == "error":
            error = event.get("error", {})
            logger.error(f"OpenAI error: {error.get('message')}")

    def _clear_output_queue(self):
        """Clear the output audio queue (for barge-in)"""
        cleared = 0
        while not self.output_audio_queue.empty():
            try:
                self.output_audio_queue.get_nowait()
                cleared += 1
            except asyncio.QueueEmpty:
                break
        if cleared > 0:
            logger.debug(f"Cleared {cleared} audio chunks from queue")

    async def _handle_function_call(self, event: dict):
        """Handle function call from OpenAI"""
        call_id = event.get("call_id")
        name = event.get("name")
        arguments = event.get("arguments", "{}")

        logger.info(f"Function call: {name}({arguments}) [tenant: {self.tenant_id}]")

        try:
            args = json.loads(arguments)
            result = await execute_tool(
                name=name,
                args=args,
                settings=self.settings,
                tenant_id=self.tenant_id,
                channel_id=self.channel_id,
                ari_handler=self.ari_handler,
                guard_extension=self.guard_extension
            )

            # Send function result back to OpenAI
            response = {
                "type": "conversation.item.create",
                "item": {
                    "type": "function_call_output",
                    "call_id": call_id,
                    "output": json.dumps(result)
                }
            }
            await self.ws.send(json.dumps(response))

            # Trigger response generation
            await self.ws.send(json.dumps({"type": "response.create"}))

        except Exception as e:
            logger.error(f"Error executing function {name}: {e}")
            # Send error back to OpenAI
            error_response = {
                "type": "conversation.item.create",
                "item": {
                    "type": "function_call_output",
                    "call_id": call_id,
                    "output": json.dumps({"error": str(e)})
                }
            }
            await self.ws.send(json.dumps(error_response))

    async def _stream_audio(self):
        """Stream audio from Asterisk to OpenAI via AudioSocket bridge"""
        logger.info(f"Audio streaming started for channel {self.channel_id}")

        if not self.audio_bridge:
            logger.warning(f"No audio bridge configured for channel {self.channel_id}")
            return

        # Set up audio callback from AudioSocket to forward to OpenAI
        def on_audio_from_asterisk(audio_data: bytes):
            """Called when audio is received from Asterisk"""
            if not self._detected_sample_rate:
                self._detect_sample_rate(audio_data)
            try:
                self.audio_buffer.put_nowait(audio_data)
            except asyncio.QueueFull:
                # Drop oldest chunk to make room (prevents latency buildup)
                try:
                    self.audio_buffer.get_nowait()
                    self.audio_buffer.put_nowait(audio_data)
                except:
                    pass

        self.audio_bridge.set_audio_callback(self.channel_id, on_audio_from_asterisk)

        # Process audio buffer and send to OpenAI
        # Use shorter timeout for lower latency (20ms = one audio chunk)
        while self.running:
            try:
                # Get audio from buffer with minimal timeout
                audio_data = await asyncio.wait_for(
                    self.audio_buffer.get(),
                    timeout=0.02  # 20ms timeout (one audio chunk)
                )
                await self.send_audio_to_openai(audio_data)

            except asyncio.TimeoutError:
                # No audio available, yield to other tasks
                await asyncio.sleep(0.001)
            except Exception as e:
                logger.error(f"Error streaming audio: {e}")

        logger.info(f"Audio streaming stopped for channel {self.channel_id}")

    async def send_audio_to_openai(self, audio_data: bytes):
        """Send audio data to OpenAI Realtime API

        AudioSocket sends 16-bit signed linear PCM at the configured sample rate.
        OpenAI pcm16 expects 16-bit signed linear PCM at 24kHz.
        We resample Asterisk → 24kHz using stateful resampler for smooth transitions.
        """
        if self.ws and self.running:
            try:
                audio_data = self._apply_noise_gate(audio_data)

                # Log input size once
                if not hasattr(self, '_logged_input'):
                    logger.info(
                        f"Input from Asterisk: {len(audio_data)} bytes "
                        f"(16-bit PCM @ {self.asterisk_sample_rate}Hz)"
                    )
                    self._logged_input = True

                # Resample Asterisk → 24kHz for OpenAI (stateful for smooth transitions)
                resampled_audio = self.resampler_to_openai.resample(audio_data)

                # Log resampled size once
                if not hasattr(self, '_logged_resampled'):
                    logger.info(
                        f"Resampled for OpenAI: {len(resampled_audio)} bytes "
                        f"(16-bit PCM @ 24kHz, ratio: {len(resampled_audio)/len(audio_data):.2f}x)"
                    )
                    self._logged_resampled = True

                audio_b64 = base64.b64encode(resampled_audio).decode()
                event = {
                    "type": "input_audio_buffer.append",
                    "audio": audio_b64
                }
                await self.ws.send(json.dumps(event))
            except Exception as e:
                logger.error(f"Error sending audio to OpenAI: {e}")

    async def _send_audio_to_asterisk(self, audio_data: bytes):
        """Queue audio data for playback to Asterisk

        OpenAI pcm16 sends 16-bit signed linear PCM at 24kHz.
        We resample to the Asterisk sample rate using stateful resampler for smooth transitions.
        """
        if not self.running:
            return

        try:
            # Log once
            if not hasattr(self, '_logged_to_asterisk'):
                logger.info(f"From OpenAI: {len(audio_data)} bytes (16-bit PCM @ 24kHz)")
                self._logged_to_asterisk = True

            # Resample 24kHz → Asterisk sample rate (stateful for smooth transitions)
            pcm_audio = self.resampler_to_asterisk.resample(audio_data)

            if not hasattr(self, '_logged_to_asterisk_out'):
                logger.info(
                    f"Resampled for Asterisk: {len(pcm_audio)} bytes (16-bit PCM @ "
                    f"{self.asterisk_sample_rate}Hz, "
                    f"ratio: {len(pcm_audio)/len(audio_data):.2f}x)"
                )
                self._logged_to_asterisk_out = True

            # Split into fixed-size chunks and queue for playback
            for i in range(0, len(pcm_audio), self.chunk_bytes):
                chunk = pcm_audio[i:i + self.chunk_bytes]
                # Pad last chunk if needed
                if len(chunk) < self.chunk_bytes:
                    chunk = chunk + b'\x00' * (self.chunk_bytes - len(chunk))
                # Queue chunk for playback (non-blocking, drop if full)
                try:
                    self.output_audio_queue.put_nowait(chunk)
                except asyncio.QueueFull:
                    self.chunks_dropped += 1
                    if self.chunks_dropped == 1 or self.chunks_dropped % 50 == 0:
                        logger.warning(f"Audio queue full! Dropped {self.chunks_dropped} chunks total")

        except Exception as e:
            logger.error(f"Error queueing audio for Asterisk: {e}")

    def _apply_noise_gate(self, audio_data: bytes) -> bytes:
        """Replace low-level noise with silence to help VAD stability."""
        if self.noise_gate_threshold <= 0 or not audio_data:
            return audio_data

        try:
            rms = audioop.rms(audio_data, BYTES_PER_SAMPLE)
        except Exception:
            return audio_data

        if rms < self.noise_gate_threshold:
            self.noise_gate_hits += 1
            if self.noise_gate_hits in (1, 100, 500):
                logger.info(
                    "Noise gate active: "
                    f"rms={rms} threshold={self.noise_gate_threshold} hits={self.noise_gate_hits}"
                )
            return b'\x00' * len(audio_data)

        if not hasattr(self, "_logged_noise_gate"):
            logger.info(f"Noise gate threshold={self.noise_gate_threshold} rms={rms}")
            self._logged_noise_gate = True

        return audio_data

    def _apply_fade(self, chunk: bytes, fade_in: bool = False, fade_out: bool = False) -> bytes:
        """Apply fade in/out to avoid clicks at chunk boundaries."""
        if not fade_in and not fade_out:
            return chunk

        # Convert to numpy array
        audio = np.frombuffer(chunk, dtype='<i2').astype(np.float32)
        n_samples = len(audio)

        # Fade duration: 2ms = 16 samples @ 8kHz
        fade_samples = min(16, n_samples // 4)

        if fade_in and fade_samples > 0:
            # Apply fade-in at start
            fade_curve = np.linspace(0, 1, fade_samples)
            audio[:fade_samples] *= fade_curve

        if fade_out and fade_samples > 0:
            # Apply fade-out at end
            fade_curve = np.linspace(1, 0, fade_samples)
            audio[-fade_samples:] *= fade_curve

        return np.clip(audio, -32768, 32767).astype('<i2').tobytes()

    async def _playback_audio(self):
        """Dedicated task for smooth audio playback to Asterisk

        CRITICAL: Must send fixed-size chunks every 20ms for natural speech.
        Uses playout buffer to absorb network jitter before starting playback.
        """
        logger.info(f"Audio playback started for channel {self.channel_id}")

        CHUNK_DURATION_NS = int(self.chunk_ms * 1_000_000)
        CHUNK_DURATION_S = self.chunk_ms / 1000.0
        LOG_INTERVAL = max(1, int(round(1.0 / CHUNK_DURATION_S)))  # Log ~1 second

        # Playout buffer: collect frames before starting playback
        PREBUFFER_FRAMES = self.playback_prebuffer_frames  # Initial buffer before playback
        MAX_SILENCE_FRAMES = max(10, int(round(0.8 / CHUNK_DURATION_S)))

        chunks_sent = 0
        session_start_ns = None
        silence_chunk = b'\x00' * self.chunk_bytes
        silence_inserted = 0
        consecutive_silence = 0
        playing = False  # True when actively playing a response
        last_chunk_was_silence = False  # Track for crossfade

        while self.running:
            try:
                if not playing:
                    # IDLE STATE: Wait for audio to arrive (blocking wait)
                    try:
                        chunk = await asyncio.wait_for(
                            self.output_audio_queue.get(),
                            timeout=1.0  # Check running flag every second
                        )
                    except asyncio.TimeoutError:
                        continue  # Just check self.running and loop

                    # Got first chunk - wait for prebuffer
                    prebuffer = [chunk]
                    prebuffer_start = time.monotonic()
                    while len(prebuffer) < PREBUFFER_FRAMES:
                        try:
                            chunk = await asyncio.wait_for(
                                self.output_audio_queue.get(),
                                timeout=0.1  # 100ms max wait per chunk
                            )
                            prebuffer.append(chunk)
                        except asyncio.TimeoutError:
                            # Timeout waiting for more - start with what we have
                            if time.monotonic() - prebuffer_start > 0.3:
                                break

                    # Start playing
                    playing = True
                    self.playback_active = True
                    session_start_ns = time.monotonic_ns()
                    chunks_sent = 0
                    consecutive_silence = 0
                    last_chunk_was_silence = True  # First chunk needs fade-in
                    logger.info(f"Starting playback with {len(prebuffer)} prebuffered frames")

                    # Send prebuffered chunks with pacing (fade-in on first)
                    for i, chunk in enumerate(prebuffer):
                        if self.channel_id in self.audio_bridge.sessions:
                            if i == 0:
                                chunk = self._apply_fade(chunk, fade_in=True)
                            expected_time_ns = session_start_ns + (chunks_sent * CHUNK_DURATION_NS)
                            wait_ns = expected_time_ns - time.monotonic_ns()
                            if wait_ns > 1_000_000:
                                await asyncio.sleep(wait_ns / 1_000_000_000)
                            await self.audio_bridge.send_audio(self.channel_id, chunk)
                            chunks_sent += 1
                    last_chunk_was_silence = False

                else:
                    # PLAYING STATE: Send chunks with precise timing
                    queue_size = self.output_audio_queue.qsize()

                    if queue_size > 0:
                        chunk = self.output_audio_queue.get_nowait()

                        # Apply fade-in if coming back from silence
                        if last_chunk_was_silence:
                            chunk = self._apply_fade(chunk, fade_in=True)

                        last_chunk_was_silence = False
                        consecutive_silence = 0
                    else:
                        # Buffer underrun - insert silence with fade
                        silence_inserted += 1
                        consecutive_silence += 1

                        # If too many consecutive silences, stop playing
                        if consecutive_silence >= MAX_SILENCE_FRAMES:
                            playing = False
                            self.playback_active = False
                            session_start_ns = None
                            logger.debug(f"Playback paused after {chunks_sent} chunks (buffer empty)")
                            continue

                        # Use silence
                        chunk = silence_chunk
                        last_chunk_was_silence = True

                    if not self.running or not self.audio_bridge:
                        break

                    # Precise timing for this chunk
                    now_ns = time.monotonic_ns()
                    expected_time_ns = session_start_ns + (chunks_sent * CHUNK_DURATION_NS)
                    wait_ns = expected_time_ns - now_ns

                    if wait_ns > 1_000_000:  # More than 1ms ahead
                        await asyncio.sleep(wait_ns / 1_000_000_000)
                    elif wait_ns < -100_000_000:  # More than 100ms behind
                        session_start_ns = now_ns - (chunks_sent * CHUNK_DURATION_NS)
                        self.playback_stats["drift_corrections"] += 1
                        logger.warning(f"Timing reset: was {-wait_ns/1_000_000:.0f}ms behind")

                    # Send the chunk
                    if self.channel_id in self.audio_bridge.sessions:
                        await self.audio_bridge.send_audio(self.channel_id, chunk)
                        chunks_sent += 1
                        self.playback_stats["chunks_sent"] = chunks_sent

                        # Log statistics periodically
                        if chunks_sent % LOG_INTERVAL == 0:
                            elapsed_s = (time.monotonic_ns() - session_start_ns) / 1_000_000_000
                            expected_s = chunks_sent * CHUNK_DURATION_S
                            drift_ms = (elapsed_s - expected_s) * 1000
                            logger.info(
                                f"Playback: {chunks_sent} chunks, queue={queue_size}, "
                                f"drift={drift_ms:+.0f}ms, silence={silence_inserted}"
                            )

            except asyncio.CancelledError:
                self.playback_active = False
                break
            except Exception as e:
                logger.error(f"Playback error: {e}")
                playing = False
                self.playback_active = False
                session_start_ns = None

        self.playback_active = False
        logger.info(f"Playback ended: {self.playback_stats['chunks_sent']} total, silence={silence_inserted}")

    async def handle_dtmf(self, digit: str):
        """Handle DTMF digit"""
        logger.debug(f"DTMF received: {digit}")
        # Could be used for menu navigation or emergency transfer

    def _detect_sample_rate(self, audio_data: bytes):
        """Best-effort detection of Asterisk sample rate from chunk size."""
        if len(audio_data) % BYTES_PER_SAMPLE != 0:
            self._detected_sample_rate = True
            return

        samples = len(audio_data) // BYTES_PER_SAMPLE
        detected = int(samples / (self.chunk_ms / 1000.0))

        if detected in (8000, 16000, 24000):
            if detected != self.asterisk_sample_rate:
                logger.warning(
                    f"Detected {detected}Hz from AudioSocket chunk ({len(audio_data)} bytes); "
                    f"overriding configured {self.asterisk_sample_rate}Hz"
                )
                self.asterisk_sample_rate = detected
                self.chunk_bytes = int(
                    self.asterisk_sample_rate * (self.chunk_ms / 1000.0) * BYTES_PER_SAMPLE
                )
                self.resampler_to_asterisk = AudioResampler(OPENAI_SAMPLE_RATE, self.asterisk_sample_rate)
                self.resampler_to_openai = AudioResampler(self.asterisk_sample_rate, OPENAI_SAMPLE_RATE)
            else:
                logger.info(
                    f"Detected {detected}Hz AudioSocket chunk size ({len(audio_data)} bytes)"
                )

        self._detected_sample_rate = True

    async def stop(self):
        """Stop the call session"""
        if not self.running:
            return

        self.running = False
        logger.info(f"Stopping call session for channel {self.channel_id}")

        # Close OpenAI WebSocket
        if self.ws:
            try:
                await self.ws.close()
            except Exception as e:
                logger.error(f"Error closing OpenAI WebSocket: {e}")

        # Hangup Asterisk channel (only if using ARI)
        if self.ari_handler:
            await self.ari_handler.hangup_channel(self.channel_id)

        # Close AudioSocket session
        if self.audio_bridge:
            await self.audio_bridge.close_session(self.channel_id)
