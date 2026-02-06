"""
Asterisk ARI Client
For backend operations like transferring calls, playing announcements, etc.
"""
import os
import logging
from typing import Optional, Dict, Any, List
import httpx

logger = logging.getLogger(__name__)


class AsteriskARIClient:
    """Client for Asterisk REST Interface (ARI)"""

    def __init__(
        self,
        base_url: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        app_name: str = "agente-portero"
    ):
        self.base_url = base_url or os.getenv("ASTERISK_ARI_URL", "http://localhost:8088/ari")
        self.username = username or os.getenv("ASTERISK_ARI_USER", "asterisk")
        self.password = password or os.getenv("ASTERISK_ARI_PASSWORD", "")
        self.app_name = app_name

        self.auth = httpx.BasicAuth(self.username, self.password)

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make authenticated request to ARI"""
        url = f"{self.base_url}{endpoint}"

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.request(
                    method,
                    url,
                    auth=self.auth,
                    params=params,
                    json=data
                )

                if response.status_code >= 400:
                    return {
                        "success": False,
                        "status": response.status_code,
                        "error": response.text
                    }

                if response.status_code == 204:
                    return {"success": True}

                return {"success": True, "data": response.json()}

        except Exception as e:
            logger.error(f"ARI request failed: {e}")
            return {"success": False, "error": str(e)}

    async def list_channels(self) -> List[Dict]:
        """List active channels"""
        result = await self._request("GET", "/channels")
        if result.get("success"):
            return result.get("data", [])
        return []

    async def get_channel(self, channel_id: str) -> Optional[Dict]:
        """Get channel details"""
        result = await self._request("GET", f"/channels/{channel_id}")
        if result.get("success"):
            return result.get("data")
        return None

    async def hangup_channel(self, channel_id: str, reason: str = "normal") -> bool:
        """Hangup a channel"""
        result = await self._request(
            "DELETE",
            f"/channels/{channel_id}",
            params={"reason": reason}
        )
        return result.get("success", False)

    async def originate_call(
        self,
        endpoint: str,
        extension: str,
        context: str = "default",
        caller_id: str = "Agente Portero",
        variables: Optional[Dict] = None
    ) -> Optional[str]:
        """
        Originate a new call

        Returns channel ID if successful
        """
        data = {
            "endpoint": endpoint,
            "extension": extension,
            "context": context,
            "callerId": caller_id,
            "app": self.app_name
        }

        if variables:
            data["variables"] = variables

        result = await self._request("POST", "/channels", data=data)

        if result.get("success"):
            return result.get("data", {}).get("id")
        return None

    async def play_sound(
        self,
        channel_id: str,
        sound: str,
        language: str = "es"
    ) -> bool:
        """Play a sound file on a channel"""
        result = await self._request(
            "POST",
            f"/channels/{channel_id}/play",
            params={"media": f"sound:{sound}", "lang": language}
        )
        return result.get("success", False)

    async def transfer_call(
        self,
        channel_id: str,
        extension: str,
        context: str = "default"
    ) -> bool:
        """Blind transfer a call to another extension"""
        # Move to Stasis app with transfer context
        result = await self._request(
            "POST",
            f"/channels/{channel_id}/redirect",
            params={
                "endpoint": f"PJSIP/{extension}@{context}"
            }
        )
        return result.get("success", False)

    async def bridge_channels(
        self,
        channel_id_1: str,
        channel_id_2: str,
        bridge_type: str = "mixing"
    ) -> Optional[str]:
        """Create a bridge between two channels"""
        # Create bridge
        bridge_result = await self._request(
            "POST",
            "/bridges",
            params={"type": bridge_type}
        )

        if not bridge_result.get("success"):
            return None

        bridge_id = bridge_result.get("data", {}).get("id")

        # Add channels to bridge
        await self._request(
            "POST",
            f"/bridges/{bridge_id}/addChannel",
            params={"channel": f"{channel_id_1},{channel_id_2}"}
        )

        return bridge_id

    async def send_dtmf(self, channel_id: str, dtmf: str) -> bool:
        """Send DTMF tones to a channel"""
        result = await self._request(
            "POST",
            f"/channels/{channel_id}/dtmf",
            params={"dtmf": dtmf}
        )
        return result.get("success", False)

    async def check_connection(self) -> bool:
        """Check if ARI is reachable"""
        result = await self._request("GET", "/asterisk/info")
        return result.get("success", False)

    async def get_asterisk_info(self) -> Optional[Dict]:
        """Get Asterisk system information"""
        result = await self._request("GET", "/asterisk/info")
        if result.get("success"):
            return result.get("data")
        return None


# Singleton instance
_client: Optional[AsteriskARIClient] = None


def get_asterisk_client() -> AsteriskARIClient:
    """Get or create ARI client singleton"""
    global _client
    if _client is None:
        _client = AsteriskARIClient()
    return _client
