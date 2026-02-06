"""
Hikvision Gate Control Client
Controls access gates via Hikvision camera/access control ISAPI
"""
import os
import logging
import asyncio
from typing import Optional, Dict, Any
import httpx

logger = logging.getLogger(__name__)


class HikvisionGateClient:
    """Client for Hikvision ISAPI.

    This client supports:
    - RemoteControlDoor (optional)
    - AccessControl provisioning: create user + assign card (QR)
    """

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
        """Open access gate (optional legacy behavior)."""
        xml_body = "<RemoteControlDoor><cmd>open</cmd></RemoteControlDoor>"

        result = await self._request(
            "PUT",
            f"/ISAPI/AccessControl/RemoteControl/door/{door_id}",
            xml_body,
        )
        if result.get("success"):
            return {"success": True, "method": "access_control"}

        # Fallback: curl digest (some firmwares behave better)
        try:
            url = f"{self.base_url}/ISAPI/AccessControl/RemoteControl/door/{door_id}"
            proc = await asyncio.create_subprocess_exec(
                "curl",
                "--silent",
                "--show-error",
                "--digest",
                "-u",
                f"{self.username}:{self.password}",
                "-X",
                "PUT",
                "-H",
                "Content-Type: application/xml",
                "--data",
                xml_body,
                "--max-time",
                str(self.timeout),
                "-o",
                "/dev/null",
                "-w",
                "%{http_code}",
                url,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            out, err = await proc.communicate()
            code = (out or b"").decode("utf-8", errors="ignore").strip()
            if code in ("200", "204"):
                return {"success": True, "method": "curl_digest"}
            return {"success": False, "error": f"curl http_code={code}", "stderr": err.decode('utf-8', errors='ignore')[:200]}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def create_user_and_card(
        self,
        *,
        employee_no: str,
        name: str,
        begin_time: str,
        end_time: str,
        card_no: str,
        door_right: str = "1",
    ) -> Dict[str, Any]:
        """Provision a person and assign a card/QR credential.

        Mirrors the proven production flow in Documents\ISAPI\v.1\api.php.
        Times are expected as local strings: YYYY-MM-DDTHH:MM:SS
        """
        user_data = {
            "UserInfo": {
                "employeeNo": employee_no,
                "name": name,
                "userType": "normal",
                "doorRight": door_right,
                "RightPlan": [{"doorNo": 1, "planTemplateNo": "1"}],
                "gender": "male",
                "Valid": {
                    "enable": True,
                    "beginTime": begin_time,
                    "endTime": end_time,
                    "timeType": "local",
                },
            }
        }

        import json as _json
        r1 = await self._request(
            "POST",
            "/ISAPI/AccessControl/UserInfo/Record?format=json",
            data=_json.dumps(user_data),
            content_type="application/json",
        )

        card_data = {
            "CardInfo": {
                "employeeNo": employee_no,
                "cardNo": card_no,
                "cardType": "normalCard",
                "cardValid": {
                    "enable": True,
                    "beginTime": begin_time,
                    "endTime": end_time,
                    "timeType": "local",
                },
            }
        }

        r2 = await self._request(
            "POST",
            "/ISAPI/AccessControl/CardInfo/Record?format=json",
            data=_json.dumps(card_data),
            content_type="application/json",
        )

        def _status_ok(resp: Dict[str, Any]) -> bool:
            if not resp.get("success"):
                return False
            body = resp.get("body") or ""
            try:
                j = _json.loads(body)
                # Many ISAPI JSON responses include {"statusCode": 1, "statusString": "OK"}
                if isinstance(j, dict) and (j.get("statusCode") in (1, "1")):
                    return True
            except Exception:
                pass
            # Fallback: accept HTTP 200/204
            return True

        ok = _status_ok(r1) and _status_ok(r2)
        return {"success": ok, "user": r1, "card": r2}


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
