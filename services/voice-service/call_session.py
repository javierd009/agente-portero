"""
Call Session - Manages a single call with OpenAI Realtime
"""
import asyncio
import json
import logging
import base64
from typing import Optional, TYPE_CHECKING, Callable
import websockets
import httpx

from config import Settings
from tools import AGENT_TOOLS, execute_tool

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
        self.audio_buffer: asyncio.Queue = asyncio.Queue(maxsize=100)

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

            # Start listening for OpenAI events and audio streaming
            listen_task = asyncio.create_task(self._listen_openai())
            stream_task = asyncio.create_task(self._stream_audio())

            # Wait for the listening task to complete (it runs until connection closes)
            # This keeps the session alive until the call ends
            await listen_task

            # Cancel streaming task when listening ends
            stream_task.cancel()
            try:
                await stream_task
            except asyncio.CancelledError:
                pass

        except Exception as e:
            logger.error(f"Failed to start OpenAI session: {e}", exc_info=True)
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
            try:
                self.audio_buffer.put_nowait(audio_data)
            except asyncio.QueueFull:
                pass  # Drop audio if buffer is full

        self.audio_bridge.set_audio_callback(self.channel_id, on_audio_from_asterisk)

        # Process audio buffer and send to OpenAI
        while self.running:
            try:
                # Get audio from buffer with timeout
                audio_data = await asyncio.wait_for(
                    self.audio_buffer.get(),
                    timeout=0.1
                )
                await self.send_audio_to_openai(audio_data)

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error streaming audio: {e}")

        logger.info(f"Audio streaming stopped for channel {self.channel_id}")

    async def send_audio_to_openai(self, audio_data: bytes):
        """Send audio data to OpenAI Realtime API"""
        if self.ws and self.running:
            try:
                audio_b64 = base64.b64encode(audio_data).decode()
                event = {
                    "type": "input_audio_buffer.append",
                    "audio": audio_b64
                }
                await self.ws.send(json.dumps(event))
            except Exception as e:
                logger.error(f"Error sending audio to OpenAI: {e}")

    async def _send_audio_to_asterisk(self, audio_data: bytes):
        """Send audio data to Asterisk channel via AudioSocket bridge"""
        if self.audio_bridge and self.running:
            try:
                await self.audio_bridge.send_audio(self.channel_id, audio_data)
            except Exception as e:
                logger.error(f"Error sending audio to Asterisk: {e}")

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

        # Hangup Asterisk channel (only if using ARI)
        if self.ari_handler:
            await self.ari_handler.hangup_channel(self.channel_id)

        # Close AudioSocket session
        if self.audio_bridge:
            await self.audio_bridge.close_session(self.channel_id)
