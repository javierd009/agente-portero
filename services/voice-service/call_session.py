"""
Call Session - Manages a single call with OpenAI Realtime
"""
import asyncio
import json
import logging
import base64
from typing import Optional, TYPE_CHECKING
import websockets
import httpx

from config import Settings
from tools import AGENT_TOOLS, execute_tool

if TYPE_CHECKING:
    from ari_handler import ARIHandler

logger = logging.getLogger(__name__)


class CallSession:
    """Manages a single call session with OpenAI Realtime API"""

    def __init__(
        self,
        channel_id: str,
        caller_id: str,
        settings: Settings,
        ari_handler: "ARIHandler"
    ):
        self.channel_id = channel_id
        self.caller_id = caller_id
        self.settings = settings
        self.ari_handler = ari_handler

        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.running = False
        self.tenant_id: Optional[str] = None  # Will be determined from extension
        self.conversation_id: Optional[str] = None

    @property
    def openai_ws_url(self) -> str:
        return f"{self.settings.openai_realtime_url}?model={self.settings.openai_realtime_model}"

    def _get_system_prompt(self) -> str:
        """Get the system prompt for the AI agent"""
        return """Eres un agente de seguridad virtual para un condominio residencial en México.
Tu trabajo es atender a los visitantes que llegan a la puerta principal.

FLUJO DE CONVERSACIÓN:
1. Saluda amablemente e identifícate como el sistema de seguridad del condominio
2. Pregunta el nombre del visitante
3. Pregunta a quién visita (nombre del residente o número de departamento)
4. Pregunta el motivo de la visita
5. Verifica si el visitante está autorizado usando las herramientas disponibles
6. Si está autorizado, informa que abrirás la puerta y notificarás al residente
7. Si no está autorizado, pide al residente que confirme o transfiere a un guardia

REGLAS:
- Sé cortés pero eficiente
- Habla en español mexicano
- Si el visitante no proporciona información clara, pide que repita
- Nunca reveles información sensible sobre los residentes
- Si detectas una situación sospechosa, transfiere a un guardia humano

HERRAMIENTAS DISPONIBLES:
- check_visitor: Verificar si un visitante está pre-autorizado
- find_resident: Buscar un residente por nombre o unidad
- notify_resident: Notificar al residente sobre el visitante
- open_gate: Abrir la puerta de acceso
- get_recent_plates: Obtener placas detectadas recientemente por las cámaras
- transfer_to_guard: Transferir la llamada a un guardia humano
"""

    async def start(self):
        """Start the OpenAI Realtime session"""
        self.running = True

        try:
            # Connect to OpenAI Realtime
            headers = {
                "Authorization": f"Bearer {self.settings.openai_api_key}",
                "OpenAI-Beta": "realtime=v1"
            }

            self.ws = await websockets.connect(
                self.openai_ws_url,
                extra_headers=headers
            )
            logger.info(f"Connected to OpenAI Realtime for channel {self.channel_id}")

            # Configure the session
            await self._configure_session()

            # Start listening for OpenAI events
            asyncio.create_task(self._listen_openai())

            # Start audio streaming from Asterisk
            asyncio.create_task(self._stream_audio())

        except Exception as e:
            logger.error(f"Failed to start OpenAI session: {e}")
            await self.stop()

    async def _configure_session(self):
        """Configure the OpenAI Realtime session"""
        config = {
            "type": "session.update",
            "session": {
                "modalities": ["text", "audio"],
                "instructions": self._get_system_prompt(),
                "voice": self.settings.default_voice,
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "input_audio_transcription": {
                    "model": "whisper-1"
                },
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.5,
                    "prefix_padding_ms": 300,
                    "silence_duration_ms": 500
                },
                "tools": AGENT_TOOLS,
                "tool_choice": "auto"
            }
        }
        await self.ws.send(json.dumps(config))
        logger.debug("OpenAI session configured")

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
            audio_b64 = event.get("delta")
            if audio_b64:
                audio_data = base64.b64decode(audio_b64)
                await self._send_audio_to_asterisk(audio_data)

        elif event_type == "response.audio_transcript.done":
            # AI finished speaking
            transcript = event.get("transcript", "")
            logger.info(f"AI said: {transcript}")

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

    async def _handle_function_call(self, event: dict):
        """Handle function call from OpenAI"""
        call_id = event.get("call_id")
        name = event.get("name")
        arguments = event.get("arguments", "{}")

        logger.info(f"Function call: {name}({arguments})")

        try:
            args = json.loads(arguments)
            result = await execute_tool(
                name,
                args,
                self.settings,
                self.tenant_id,
                self.channel_id
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
        """Stream audio from Asterisk to OpenAI"""
        # This would use Asterisk's external media feature
        # For now, we'll set up the infrastructure
        logger.info(f"Audio streaming started for channel {self.channel_id}")

        # In production, this would:
        # 1. Receive RTP audio from Asterisk external media
        # 2. Convert to PCM16 if needed
        # 3. Send to OpenAI via WebSocket

        while self.running:
            await asyncio.sleep(0.1)

    async def send_audio_to_openai(self, audio_data: bytes):
        """Send audio data to OpenAI"""
        if self.ws and self.running:
            audio_b64 = base64.b64encode(audio_data).decode()
            event = {
                "type": "input_audio_buffer.append",
                "audio": audio_b64
            }
            await self.ws.send(json.dumps(event))

    async def _send_audio_to_asterisk(self, audio_data: bytes):
        """Send audio data to Asterisk channel"""
        # This would send audio via external media
        # Implementation depends on your Asterisk setup
        pass

    async def handle_dtmf(self, digit: str):
        """Handle DTMF digit"""
        logger.debug(f"DTMF received: {digit}")
        # Could be used for menu navigation or emergency transfer

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

        # Hangup Asterisk channel
        await self.ari_handler.hangup_channel(self.channel_id)
