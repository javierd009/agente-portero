"""
Evolution API Client
Handles sending/receiving WhatsApp messages
"""
import httpx
import structlog
from typing import Optional, Dict, Any, List
from config import settings

logger = structlog.get_logger()


class EvolutionAPIClient:
    """Client for Evolution API (WhatsApp Business)"""

    def __init__(self):
        self.base_url = settings.EVOLUTION_API_URL
        self.api_key = settings.EVOLUTION_API_KEY
        self.instance = settings.EVOLUTION_INSTANCE
        self.headers = {
            "apikey": self.api_key,
            "Content-Type": "application/json"
        }

    async def send_text(
        self,
        phone: str,
        message: str,
        quoted_msg_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send text message to WhatsApp number

        Args:
            phone: Destination phone (5215512345678 format)
            message: Text message
            quoted_msg_id: Optional message ID to quote (reply)

        Returns:
            Response from Evolution API
        """
        url = f"{self.base_url}/message/sendText/{self.instance}"

        payload = {
            "number": phone,
            "text": message
        }

        if quoted_msg_id:
            payload["quoted"] = {"key": {"id": quoted_msg_id}}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    headers=self.headers,
                    json=payload,
                    timeout=10.0
                )
                response.raise_for_status()

                logger.info("whatsapp_message_sent", phone=phone, message_preview=message[:50])
                return response.json()

        except httpx.HTTPError as e:
            logger.error("whatsapp_send_failed", error=str(e), phone=phone)
            raise

    async def send_buttons(
        self,
        phone: str,
        message: str,
        buttons: List[str],
        footer: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send message with interactive buttons

        Args:
            phone: Destination phone
            message: Message text
            buttons: List of button labels (max 3)
            footer: Optional footer text

        Example:
            await send_buttons(
                "5215512345678",
                "¿Autorizar a Juan Pérez?",
                ["✅ Sí", "❌ No"]
            )
        """
        url = f"{self.base_url}/message/sendButtons/{self.instance}"

        button_objects = [
            {"type": "replyButton", "displayText": btn}
            for btn in buttons[:3]  # Max 3 buttons
        ]

        payload = {
            "number": phone,
            "options": {
                "body": message,
                "footer": footer or "",
                "buttons": button_objects
            }
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    headers=self.headers,
                    json=payload,
                    timeout=10.0
                )
                response.raise_for_status()

                logger.info("whatsapp_buttons_sent", phone=phone, buttons=len(buttons))
                return response.json()

        except httpx.HTTPError as e:
            logger.error("whatsapp_buttons_failed", error=str(e), phone=phone)
            raise

    async def send_media(
        self,
        phone: str,
        media_url: str,
        caption: Optional[str] = None,
        media_type: str = "image"
    ) -> Dict[str, Any]:
        """
        Send media (image, video, document)

        Args:
            phone: Destination phone
            media_url: Public URL of media file
            caption: Optional caption
            media_type: "image" | "video" | "document" | "audio"
        """
        url = f"{self.base_url}/message/sendMedia/{self.instance}"

        payload = {
            "number": phone,
            "mediatype": media_type,
            "media": media_url,
            "caption": caption or ""
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    headers=self.headers,
                    json=payload,
                    timeout=15.0
                )
                response.raise_for_status()

                logger.info("whatsapp_media_sent", phone=phone, type=media_type)
                return response.json()

        except httpx.HTTPError as e:
            logger.error("whatsapp_media_failed", error=str(e), phone=phone)
            raise

    async def mark_as_read(self, message_id: str) -> None:
        """Mark message as read"""
        url = f"{self.base_url}/chat/markMessageAsRead/{self.instance}"

        payload = {
            "readMessages": [{"id": message_id}]
        }

        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    url,
                    headers=self.headers,
                    json=payload,
                    timeout=5.0
                )
        except httpx.HTTPError as e:
            logger.warning("mark_read_failed", error=str(e))

    async def get_instance_status(self) -> Dict[str, Any]:
        """Get Evolution API instance status"""
        url = f"{self.base_url}/instance/connectionState/{self.instance}"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers=self.headers,
                    timeout=5.0
                )
                response.raise_for_status()
                return response.json()

        except httpx.HTTPError as e:
            logger.error("instance_status_failed", error=str(e))
            raise

    async def download_media(self, message_data: Dict[str, Any]) -> Optional[bytes]:
        """
        Download media (audio, image, etc.) from a message

        Args:
            message_data: The message data containing media info

        Returns:
            Media bytes or None if download fails
        """
        import base64

        try:
            message_content = message_data.get("message", {})
            message_key = message_data.get("key", {})

            logger.info("download_media_attempt", key=message_key, has_audio="audioMessage" in message_content)

            # Check for audio message
            if "audioMessage" not in message_content:
                logger.warning("no_audio_in_message")
                return None

            # Use Evolution API to get media
            url = f"{self.base_url}/chat/getBase64FromMediaMessage/{self.instance}"

            # Evolution API expects the full message structure
            payload = {
                "message": {
                    "key": {
                        "remoteJid": message_key.get("remoteJid"),
                        "fromMe": message_key.get("fromMe", False),
                        "id": message_key.get("id")
                    },
                    "message": message_content
                },
                "convertToMp4": False
            }

            logger.info("evolution_media_request", url=url)

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    headers=self.headers,
                    json=payload,
                    timeout=30.0
                )

                if response.status_code != 200:
                    logger.error("evolution_media_error", status=response.status_code, body=response.text[:200])
                    return None

                result = response.json()
                logger.info("evolution_media_response", has_base64="base64" in result)

                # Decode base64
                base64_data = result.get("base64", "")
                if base64_data:
                    # Remove data URL prefix if present (e.g., "data:audio/ogg;base64,...")
                    if "," in base64_data:
                        base64_data = base64_data.split(",")[1]

                    audio_bytes = base64.b64decode(base64_data)
                    logger.info("audio_downloaded", size_bytes=len(audio_bytes))
                    return audio_bytes

            logger.warning("no_base64_in_response")
            return None

        except Exception as e:
            logger.error("media_download_failed", error=str(e), error_type=type(e).__name__)
            return None


# Singleton instance
evolution_client = EvolutionAPIClient()
