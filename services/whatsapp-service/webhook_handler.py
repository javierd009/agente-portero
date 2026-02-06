"""
Webhook Handler for Evolution API
Processes incoming WhatsApp messages and triggers appropriate actions
"""
import httpx
import structlog
from typing import Dict, Any
from datetime import datetime

from evolution_client import evolution_client
from nlp_parser import (
    parse_intent,
    AuthorizeVisitorIntent,
    OpenGateIntent,
    CreateReportIntent,
    QueryLogsIntent,
    UnknownIntent,
)
from security_agent import get_agent_response
from audio_transcriber import transcribe_audio
from config import settings
from fast_path import parse_fast_command, execute_fast_open

logger = structlog.get_logger()


class WebhookHandler:
    """Handle incoming WhatsApp webhooks from Evolution API"""

    def __init__(self):
        self.backend_url = settings.BACKEND_API_URL
        self.backend_headers = {
            "Authorization": f"Bearer {settings.BACKEND_API_KEY}"
        } if settings.BACKEND_API_KEY else {}

    async def process_message(self, webhook_data: Dict[str, Any]) -> None:
        """
        Process incoming WhatsApp message

        Args:
            webhook_data: Webhook payload from Evolution API
        """
        try:
            # Extract message data
            event_type = webhook_data.get("event")
            if event_type != "messages.upsert":
                return  # Ignore non-message events

            message_data = webhook_data.get("data", {})
            message_info = message_data.get("key", {})
            message_content = message_data.get("message", {})

            # Extract sender phone and message text
            phone = message_info.get("remoteJid", "").replace("@s.whatsapp.net", "")
            message_id = message_info.get("id")

            # Get text from different message types
            text = None
            is_audio = False

            if "conversation" in message_content:
                text = message_content["conversation"]
            elif "extendedTextMessage" in message_content:
                text = message_content["extendedTextMessage"].get("text")
            elif "buttonsResponseMessage" in message_content:
                # User clicked a button
                text = message_content["buttonsResponseMessage"].get("selectedDisplayText")
            elif "audioMessage" in message_content:
                # Audio message - need to transcribe
                is_audio = True
                logger.info("audio_message_received", phone=phone, message_id=message_id)

                # Download and transcribe audio
                audio_bytes = await evolution_client.download_media(message_data)
                if audio_bytes:
                    text = await transcribe_audio(audio_bytes)
                    if text:
                        logger.info("audio_transcribed", phone=phone, text_preview=text[:50])
                    else:
                        await evolution_client.send_text(
                            phone,
                            "No pude entender el audio. ¿Podrías escribirlo o repetirlo?\n\n"
                            "I couldn't understand the audio. Could you type it or try again?"
                        )
                        return
                else:
                    await evolution_client.send_text(
                        phone,
                        "No pude descargar el audio. Intenta de nuevo.\n\n"
                        "Couldn't download the audio. Please try again."
                    )
                    return

            if not text:
                logger.debug("message_no_text", phone=phone)
                return

            logger.info(
                "message_received",
                phone=phone,
                message=text[:100],
                message_id=message_id
            )

            # Mark as read
            await evolution_client.mark_as_read(message_id)

            # Get resident from backend (may be None for visitors)
            resident = await self._get_resident_by_phone(phone)

            # If not a registered resident, ask them to register with administration
            # NOTE: Only residents use WhatsApp. Visitors call via intercom.
            if not resident:
                await self._handle_unregistered_number(phone, text)
                return

            # FAST PATH (no LLM): instant open commands
            if settings.ENABLE_REMOTE_GATE_OPEN:
                fast_cmd = parse_fast_command(text)
                if fast_cmd:
                    await evolution_client.send_text(phone, "Abriendo…")
                    ok, msg, log_ctx = await execute_fast_open(fast_cmd.target)

                    # Best-effort logging (do not block response)
                    try:
                        async with httpx.AsyncClient(timeout=2.0) as client:
                            await client.post(
                                f"{self.backend_url}/api/v1/audit/log-open",
                                headers={
                                    **self.backend_headers,
                                    "x-tenant-id": resident["condominium_id"],
                                },
                                json={
                                    "access_point": log_ctx.get("access_point"),
                                    "success": bool(ok),
                                    "actor_channel": "whatsapp",
                                    "actor_phone": phone,
                                    "message_id": message_id,
                                    "resident_id": resident.get("id"),
                                    "device_host": log_ctx.get("device_host"),
                                    "door_id": log_ctx.get("door_id"),
                                    "method": "fast_path_isapi",
                                },
                            )
                    except Exception as e:
                        logger.warn("fast_open_log_failed", error=str(e))

                    await evolution_client.send_text(phone, msg)
                    return

            # Parse intent (LLM)
            intent = await parse_intent(text)

            # Route to appropriate handler
            if isinstance(intent, AuthorizeVisitorIntent):
                await self._handle_authorize_visitor(phone, resident, intent)

            elif isinstance(intent, OpenGateIntent):
                await self._handle_open_gate(phone, resident, intent)

            elif isinstance(intent, CreateReportIntent):
                await self._handle_create_report(phone, resident, intent)

            elif isinstance(intent, QueryLogsIntent):
                await self._handle_query_logs(phone, resident, intent)

            elif isinstance(intent, UnknownIntent):
                await self._handle_unknown(phone, text, resident)

        except Exception as e:
            logger.error("webhook_process_error", error=str(e))

    async def _get_resident_by_phone(self, phone: str) -> Dict[str, Any] | None:
        """Get resident data from backend"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.backend_url}/api/v1/residents/by-phone/{phone}",
                    headers=self.backend_headers,
                    timeout=5.0
                )
                if response.status_code == 200:
                    return response.json()
                return None
        except Exception as e:
            logger.error("get_resident_error", error=str(e), phone=phone)
            return None

    async def _handle_authorize_visitor(
        self,
        phone: str,
        resident: Dict[str, Any],
        intent: AuthorizeVisitorIntent
    ) -> None:
        """Handle visitor authorization"""
        try:
            # Create temporary authorization in backend
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.backend_url}/api/v1/visitors/authorize",
                    headers=self.backend_headers,
                    json={
                        "condominium_id": resident["condominium_id"],
                        "resident_id": resident["id"],
                        "visitor_name": intent.visitor_name,
                        "vehicle_plate": intent.visitor_vehicle_plate,
                        "valid_until": intent.valid_until.isoformat() if intent.valid_until else None,
                        "notes": intent.notes or f"Autorizado via WhatsApp por {resident['name']}"
                    },
                    timeout=10.0
                )

                if response.status_code == 201:
                    visitor_data = response.json()
                    valid_until = datetime.fromisoformat(visitor_data["valid_until"])

                    # Success response
                    message = f"""✅ Visitante autorizado

👤 Nombre: {intent.visitor_name}
🚗 Placa: {intent.visitor_vehicle_plate or "No especificada"}
⏰ Válido hasta: {valid_until.strftime("%d/%m %H:%M")}

Cuando llegue, la puerta se abrirá automáticamente y te enviaré una notificación."""

                    await evolution_client.send_text(phone, message)

                    logger.info(
                        "visitor_authorized",
                        resident_id=resident["id"],
                        visitor_name=intent.visitor_name
                    )
                else:
                    await evolution_client.send_text(
                        phone,
                        "❌ Error al autorizar visitante. Intenta de nuevo."
                    )

        except Exception as e:
            logger.error("authorize_visitor_error", error=str(e))
            await evolution_client.send_text(
                phone,
                "❌ Error al procesar autorización. Intenta más tarde."
            )

    async def _handle_open_gate(
        self,
        phone: str,
        resident: Dict[str, Any],
        intent: OpenGateIntent
    ) -> None:
        """Handle remote gate opening"""
        try:
            # Call backend to open gate
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.backend_url}/api/v1/gates/open",
                    headers=self.backend_headers,
                    json={
                        "condominium_id": resident["condominium_id"],
                        "resident_id": resident["id"],
                        "gate_name": intent.gate_name,
                        "method": "whatsapp_remote"
                    },
                    timeout=10.0
                )

                if response.status_code == 200:
                    gate_data = response.json()

                    # Send success message with photo (if available)
                    message = f"""✅ Puerta {intent.gate_name} abierta

🕐 Hora: {datetime.utcnow().strftime("%H:%M:%S")}
👤 Solicitado por: {resident['name']}"""

                    await evolution_client.send_text(phone, message)

                    # Send photo if available
                    if gate_data.get("snapshot_url"):
                        await evolution_client.send_media(
                            phone,
                            gate_data["snapshot_url"],
                            caption="📸 Captura del momento"
                        )

                    logger.info(
                        "gate_opened_remotely",
                        resident_id=resident["id"],
                        gate=intent.gate_name
                    )
                else:
                    await evolution_client.send_text(
                        phone,
                        "❌ Error al abrir puerta. Verifica tu conexión."
                    )

        except Exception as e:
            logger.error("open_gate_error", error=str(e))
            await evolution_client.send_text(
                phone,
                "❌ Error al abrir puerta. Intenta más tarde."
            )

    async def _handle_create_report(
        self,
        phone: str,
        resident: Dict[str, Any],
        intent: CreateReportIntent
    ) -> None:
        """Handle incident report creation"""
        try:
            # Create report in backend
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.backend_url}/api/v1/reports",
                    headers=self.backend_headers,
                    json={
                        "condominium_id": resident["condominium_id"],
                        "resident_id": resident["id"],
                        "report_type": intent.report_type,
                        "description": intent.description,
                        "location": intent.location,
                        "urgency": intent.urgency,
                        "source": "whatsapp"
                    },
                    timeout=10.0
                )

                if response.status_code == 201:
                    report_data = response.json()

                    message = f"""✅ Reporte creado

📋 Folio: #{report_data['id'][:8]}
📝 Tipo: {intent.report_type}
📍 Ubicación: {intent.location or "No especificada"}
⚠️ Urgencia: {intent.urgency}

El administrador ha sido notificado."""

                    await evolution_client.send_text(phone, message)

                    logger.info(
                        "report_created",
                        resident_id=resident["id"],
                        report_id=report_data["id"],
                        type=intent.report_type
                    )
                else:
                    await evolution_client.send_text(
                        phone,
                        "❌ Error al crear reporte. Intenta de nuevo."
                    )

        except Exception as e:
            logger.error("create_report_error", error=str(e))
            await evolution_client.send_text(
                phone,
                "❌ Error al procesar reporte. Intenta más tarde."
            )

    async def _handle_query_logs(
        self,
        phone: str,
        resident: Dict[str, Any],
        intent: QueryLogsIntent
    ) -> None:
        """Handle access logs query"""
        try:
            # Query backend for logs
            async with httpx.AsyncClient() as client:
                params = {
                    "resident_id": resident["id"],
                    "query_type": intent.query_type
                }
                if intent.visitor_name:
                    params["visitor_name"] = intent.visitor_name

                response = await client.get(
                    f"{self.backend_url}/api/v1/access/logs",
                    headers=self.backend_headers,
                    params=params,
                    timeout=10.0
                )

                if response.status_code == 200:
                    logs = response.json()

                    if not logs:
                        await evolution_client.send_text(
                            phone,
                            "📋 No hay registros para el período solicitado."
                        )
                        return

                    # Format logs as message
                    message_lines = [f"📋 Registros de acceso ({intent.query_type})\n"]

                    for log in logs[:10]:  # Limit to 10 most recent
                        timestamp = datetime.fromisoformat(log["created_at"])
                        message_lines.append(
                            f"• {timestamp.strftime('%d/%m %H:%M')} - "
                            f"{log.get('visitor_name', 'Sin nombre')} "
                            f"({log['event_type']})"
                        )

                    if len(logs) > 10:
                        message_lines.append(f"\n... y {len(logs) - 10} más")

                    await evolution_client.send_text(
                        phone,
                        "\n".join(message_lines)
                    )

                    logger.info(
                        "logs_queried",
                        resident_id=resident["id"],
                        query_type=intent.query_type,
                        results=len(logs)
                    )

        except Exception as e:
            logger.error("query_logs_error", error=str(e))
            await evolution_client.send_text(
                phone,
                "❌ Error al consultar logs. Intenta más tarde."
            )

    async def _handle_unknown(self, phone: str, message: str, resident: Dict[str, Any]) -> None:
        """Handle unknown intent - use AI agent for natural conversation"""
        try:
            # Use AI security agent for conversational response
            response = await get_agent_response(
                phone=phone,
                message=message,
                resident_info=resident
            )
            await evolution_client.send_text(phone, response)

        except Exception as e:
            logger.error("ai_agent_error", error=str(e))
            # Fallback to help text
            help_text = """🤖 ¿Cómo puedo ayudarte?

📥 *Autorizar visitante:* "Viene Juan Pérez"
🚪 *Abrir puerta:* "Abrir puerta"
📝 *Reportar:* "Reportar: luz fundida"
📋 *Consultar:* "¿Quién vino hoy?"

I can also help you in English!"""
            await evolution_client.send_text(phone, help_text)

    async def _handle_unregistered_number(self, phone: str, message: str) -> None:
        """
        Handle messages from unregistered phone numbers.

        WhatsApp is only for registered residents. Visitors use the intercom.
        Unregistered numbers should contact administration to be registered.
        """
        logger.info(
            "unregistered_number_message",
            phone=phone[-4:],
            message_preview=message[:50]
        )

        # Send registration instructions in Spanish and English
        response = """⚠️ *Número no registrado*

Este servicio de WhatsApp es exclusivo para residentes registrados del condominio.

Si eres residente y aún no estás registrado, por favor contacta a la administración para agregar tu número.

Si eres visitante, por favor usa el interfón en la entrada para comunicarte con seguridad.

---

⚠️ *Unregistered Number*

This WhatsApp service is exclusively for registered condominium residents.

If you are a resident and not yet registered, please contact administration to add your phone number.

If you are a visitor, please use the intercom at the entrance to contact security."""

        await evolution_client.send_text(phone, response)


# Singleton instance
webhook_handler = WebhookHandler()
