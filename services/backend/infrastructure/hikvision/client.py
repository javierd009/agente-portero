"""
Hikvision Gate Control Client
Controls access gates via Hikvision camera/access control ISAPI
"""
import os
import logging
from typing import Optional, Dict, Any
import httpx

logger = logging.getLogger(__name__)


class HikvisionGateClient:
    """Client for Hikvision gate control via ISAPI"""

    def __init__(
        self,
        host: Optional[str] = None,
        port: int = 80,
        username: Optional[str] = None,
        password: Optional[str] = None
    ):
        self.host = host or os.getenv("HIKVISION_HOST", "192.168.1.100")
        self.port = port or int(os.getenv("HIKVISION_PORT", "80"))
        self.username = username or os.getenv("HIKVISION_USER", "admin")
        self.password = password or os.getenv("HIKVISION_PASSWORD", "")

        self.base_url = f"http://{self.host}:{self.port}"
        self.auth = httpx.DigestAuth(self.username, self.password)
        self.timeout = float(os.getenv("HIKVISION_TIMEOUT", "3"))

    async def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[str] = None,
        content_type: str = "application/xml"
    ) -> Dict[str, Any]:
        """Make authenticated request to Hikvision device"""
        url = f"{self.base_url}{endpoint}"
        headers = {"Content-Type": content_type} if data else {}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.request(
                    method,
                    url,
                    auth=self.auth,
                    content=data,
                    headers=headers
                )

                return {
                    "success": response.status_code in (200, 204),
                    "status": response.status_code,
                    "body": response.text
                }

        except Exception as e:
            logger.error(f"Hikvision request failed: {e}")
            return {"success": False, "error": str(e)}

    async def open_gate(self, door_id: int = 1) -> Dict[str, Any]:
        """
        Open access gate

        Args:
            door_id: Door/gate number (usually 1)
        """
        # Try multiple approaches depending on device type

        # Approach 1: Access Control door command
        # NOTE: Some Hikvision ACS firmwares are picky about whitespace / XML declaration.
        # Use a minimal one-line payload first.
        xml_body = "<RemoteControlDoor><cmd>open</cmd></RemoteControlDoor>"

        result = await self._request(
            "PUT",
            f"/ISAPI/AccessControl/RemoteControl/door/{door_id}",
            xml_body
        )

        if result.get("success"):
            logger.info(f"Gate {door_id} opened via AccessControl")
            return {"success": True, "method": "access_control"}

        # Approach 1b: Access Control door command (ISAPI v2 namespace; required by some panels)
        xml_body_v2 = (
            "<RemoteControlDoor version='2.0' xmlns='http://www.isapi.org/ver20/XMLSchema'>"
            "<cmd>open</cmd>"
            "</RemoteControlDoor>"
        )

        result = await self._request(
            "PUT",
            f"/ISAPI/AccessControl/RemoteControl/door/{door_id}",
            xml_body_v2
        )

        if result.get("success"):
            logger.info(f"Gate {door_id} opened via AccessControl (v2)")
            return {"success": True, "method": "access_control_v2"}

        # Approach 2: IO Trigger (for cameras with alarm output)
        result = await self._request(
            "PUT",
            f"/ISAPI/System/IO/outputs/{door_id}/trigger"
        )

        if result.get("success"):
            logger.info(f"Gate {door_id} opened via IO trigger")
            return {"success": True, "method": "io_trigger"}

        # Approach 3: Alarm output
        xml_body = """<?xml version="1.0" encoding="UTF-8"?>
        <IOOutputPort>
            <outputState>active</outputState>
        </IOOutputPort>"""

        result = await self._request(
            "PUT",
            f"/ISAPI/System/IO/outputs/{door_id}",
            xml_body
        )

        if result.get("success"):
            logger.info(f"Gate {door_id} opened via alarm output")
            return {"success": True, "method": "alarm_output"}

        logger.error(f"Failed to open gate {door_id}")
        return {"success": False, "error": "All methods failed"}

    async def close_gate(self, door_id: int = 1) -> Dict[str, Any]:
        """Close access gate (if supported)"""
        # Minimal payload (avoid XML declaration/whitespace issues)
        xml_body = "<RemoteControlDoor><cmd>close</cmd></RemoteControlDoor>"

        result = await self._request(
            "PUT",
            f"/ISAPI/AccessControl/RemoteControl/door/{door_id}",
            xml_body
        )

        if result.get("success"):
            return result

        # Fallback: ISAPI v2 namespace
        xml_body_v2 = (
            "<RemoteControlDoor version='2.0' xmlns='http://www.isapi.org/ver20/XMLSchema'>"
            "<cmd>close</cmd>"
            "</RemoteControlDoor>"
        )

        return await self._request(
            "PUT",
            f"/ISAPI/AccessControl/RemoteControl/door/{door_id}",
            xml_body_v2
        )

    async def get_device_info(self) -> Dict[str, Any]:
        """Get device information"""
        result = await self._request("GET", "/ISAPI/System/deviceInfo")

        if result.get("success"):
            # Parse basic info from XML
            body = result.get("body", "")
            return {
                "success": True,
                "connected": True,
                "raw": body
            }

        return {"success": False, "connected": False}

    async def get_door_status(self, door_id: int = 1) -> Dict[str, Any]:
        """Get door/gate status"""
        result = await self._request(
            "GET",
            f"/ISAPI/AccessControl/Door/status/{door_id}"
        )
        return result

    async def check_connection(self) -> bool:
        """Check if device is reachable"""
        result = await self.get_device_info()
        return result.get("connected", False)


# Gate clients per condominium (cached by host)
_clients: Dict[str, HikvisionGateClient] = {}


def get_gate_client(
    host: Optional[str] = None,
    port: int = 80,
    username: Optional[str] = None,
    password: Optional[str] = None
) -> HikvisionGateClient:
    """Get or create gate client for a specific host"""
    key = f"{host}:{port}"

    if key not in _clients:
        _clients[key] = HikvisionGateClient(
            host=host,
            port=port,
            username=username,
            password=password
        )

    return _clients[key]
