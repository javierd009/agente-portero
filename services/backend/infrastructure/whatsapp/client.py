"""
Evolution API Client
WhatsApp messaging via Evolution API
https://github.com/EvolutionAPI/evolution-api
"""
import os
import logging
from typing import Optional, Dict, Any, List
import httpx

logger = logging.getLogger(__name__)


class EvolutionAPIClient:
    """Client for Evolution API WhatsApp gateway"""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        instance_name: Optional[str] = None
    ):
        self.base_url = base_url or os.getenv("EVOLUTION_API_URL", "http://localhost:8080")
        self.api_key = api_key or os.getenv("EVOLUTION_API_KEY", "")
        self.instance_name = instance_name or os.getenv("EVOLUTION_INSTANCE", "agente-portero")

        self.headers = {
            "Content-Type": "application/json",
            "apikey": self.api_key
        }

    async def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make request to Evolution API"""
        url = f"{self.base_url}/{endpoint}"

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.request(
                    method,
                    url,
                    headers=self.headers,
                    json=data
                )

                if response.status_code >= 400:
                    logger.error(f"Evolution API error: {response.status_code} - {response.text}")
                    return {"error": response.text, "status": response.status_code}

                return response.json()

        except Exception as e:
            logger.error(f"Evolution API request failed: {e}")
            return {"error": str(e)}

    async def check_instance_status(self) -> Dict[str, Any]:
        """Check if WhatsApp instance is connected"""
        return await self._request(
            "GET",
            f"instance/connectionState/{self.instance_name}"
        )

    async def create_instance(self) -> Dict[str, Any]:
        """Create a new WhatsApp instance"""
        data = {
            "instanceName": self.instance_name,
            "qrcode": True,
            "integration": "WHATSAPP-BAILEYS"
        }
        return await self._request("POST", "instance/create", data)

    async def get_qr_code(self) -> Dict[str, Any]:
        """Get QR code for WhatsApp connection"""
        return await self._request(
            "GET",
            f"instance/qrcode/{self.instance_name}"
        )

    async def send_text_message(
        self,
        phone: str,
        message: str
    ) -> Dict[str, Any]:
        """
        Send a text message

        Args:
            phone: Phone number with country code (e.g., "521234567890")
            message: Text message to send
        """
        # Normalize phone number
        phone = self._normalize_phone(phone)

        data = {
            "number": phone,
            "text": message
        }

        result = await self._request(
            "POST",
            f"message/sendText/{self.instance_name}",
            data
        )

        if "error" not in result:
            logger.info(f"WhatsApp message sent to {phone}")
        else:
            logger.error(f"Failed to send WhatsApp to {phone}: {result}")

        return result

    async def send_media_message(
        self,
        phone: str,
        media_url: str,
        caption: Optional[str] = None,
        media_type: str = "image"
    ) -> Dict[str, Any]:
        """
        Send a media message (image, video, document)

        Args:
            phone: Phone number with country code
            media_url: URL of the media file
            caption: Optional caption for the media
            media_type: Type of media (image, video, document)
        """
        phone = self._normalize_phone(phone)

        data = {
            "number": phone,
            "mediatype": media_type,
            "media": media_url,
        }

        if caption:
            data["caption"] = caption

        return await self._request(
            "POST",
            f"message/sendMedia/{self.instance_name}",
            data
        )

    async def send_buttons_message(
        self,
        phone: str,
        title: str,
        description: str,
        buttons: List[Dict[str, str]],
        footer: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send a message with buttons

        Args:
            phone: Phone number
            title: Message title
            description: Message body
            buttons: List of buttons [{"buttonId": "1", "buttonText": {"displayText": "Yes"}}]
            footer: Optional footer text
        """
        phone = self._normalize_phone(phone)

        data = {
            "number": phone,
            "title": title,
            "description": description,
            "buttons": buttons
        }

        if footer:
            data["footer"] = footer

        return await self._request(
            "POST",
            f"message/sendButtons/{self.instance_name}",
            data
        )

    async def send_visitor_notification(
        self,
        phone: str,
        visitor_name: str,
        visitor_reason: Optional[str] = None,
        plate: Optional[str] = None,
        snapshot_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send visitor arrival notification to resident

        Args:
            phone: Resident's WhatsApp number
            visitor_name: Name of the visitor
            visitor_reason: Reason for visit
            plate: Vehicle plate if available
            snapshot_url: Camera snapshot URL
        """
        # Build message
        message_parts = [
            f"🔔 *Visitante en puerta*",
            f"",
            f"👤 *Nombre:* {visitor_name}"
        ]

        if visitor_reason:
            message_parts.append(f"📝 *Motivo:* {visitor_reason}")

        if plate:
            message_parts.append(f"🚗 *Placa:* {plate}")

        message_parts.append("")
        message_parts.append("_Responde 'OK' para autorizar entrada_")

        message = "\n".join(message_parts)

        # Send with image if available
        if snapshot_url:
            return await self.send_media_message(
                phone=phone,
                media_url=snapshot_url,
                caption=message,
                media_type="image"
            )
        else:
            return await self.send_text_message(phone, message)

    async def send_access_granted_notification(
        self,
        phone: str,
        visitor_name: str,
        access_point: str = "Entrada principal"
    ) -> Dict[str, Any]:
        """Notify resident that access was granted"""
        message = (
            f"✅ *Acceso autorizado*\n\n"
            f"👤 {visitor_name}\n"
            f"🚪 {access_point}\n\n"
            f"_El visitante ha ingresado_"
        )
        return await self.send_text_message(phone, message)

    async def send_access_denied_alert(
        self,
        phone: str,
        reason: str,
        details: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send alert about denied access attempt"""
        message = f"⚠️ *Acceso denegado*\n\n📝 {reason}"
        if details:
            message += f"\n\n{details}"

        return await self.send_text_message(phone, message)

    def _normalize_phone(self, phone: str) -> str:
        """Normalize phone number to required format"""
        # Remove spaces, dashes, and parentheses
        phone = "".join(c for c in phone if c.isdigit() or c == "+")

        # Remove leading +
        if phone.startswith("+"):
            phone = phone[1:]

        # Add Mexico country code if not present
        if len(phone) == 10:
            phone = "52" + phone

        return phone


# Singleton instance
_client: Optional[EvolutionAPIClient] = None


def get_whatsapp_client() -> EvolutionAPIClient:
    """Get or create WhatsApp client singleton"""
    global _client
    if _client is None:
        _client = EvolutionAPIClient()
    return _client
