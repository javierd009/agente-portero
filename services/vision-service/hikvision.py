"""
Hikvision Camera Client
ISAPI integration for camera control and event streaming
"""
import asyncio
import logging
from typing import Optional, List, Dict, Any
import xml.etree.ElementTree as ET
from io import BytesIO

import httpx
import numpy as np
from PIL import Image

from config import Settings

logger = logging.getLogger(__name__)


class HikvisionClient:
    """Client for Hikvision cameras using ISAPI"""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.base_url = f"http://{settings.hikvision_host}:{settings.hikvision_port}"
        self.auth = httpx.DigestAuth(settings.hikvision_user, settings.hikvision_password)

    async def _request(
        self,
        method: str,
        path: str,
        **kwargs
    ) -> Optional[httpx.Response]:
        """Make authenticated request to camera"""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                url = f"{self.base_url}{path}"
                resp = await client.request(method, url, auth=self.auth, **kwargs)
                return resp
        except Exception as e:
            logger.error(f"Hikvision request error: {e}")
            return None

    async def list_cameras(self) -> List[Dict[str, Any]]:
        """List available camera channels"""
        cameras = []

        resp = await self._request("GET", "/ISAPI/System/Video/inputs/channels")
        if resp and resp.status_code == 200:
            try:
                root = ET.fromstring(resp.content)
                ns = {"hik": "http://www.hikvision.com/ver20/XMLSchema"}

                for channel in root.findall(".//hik:VideoInputChannel", ns):
                    camera = {
                        "id": channel.find("hik:id", ns).text if channel.find("hik:id", ns) is not None else None,
                        "name": channel.find("hik:name", ns).text if channel.find("hik:name", ns) is not None else None,
                        "enabled": channel.find("hik:enabled", ns).text == "true" if channel.find("hik:enabled", ns) is not None else False
                    }
                    cameras.append(camera)
            except Exception as e:
                logger.error(f"Failed to parse camera list: {e}")

        # Fallback: try single camera
        if not cameras:
            resp = await self._request("GET", "/ISAPI/System/deviceInfo")
            if resp and resp.status_code == 200:
                cameras.append({
                    "id": "1",
                    "name": "Main Camera",
                    "enabled": True
                })

        return cameras

    async def get_snapshot(self, channel_id: str = "1") -> Optional[np.ndarray]:
        """Get snapshot from camera channel"""
        # Try different snapshot endpoints
        endpoints = [
            f"/ISAPI/Streaming/channels/{channel_id}/picture",
            f"/ISAPI/Streaming/channels/{channel_id}01/picture",
            f"/Streaming/channels/{channel_id}/picture",
            "/ISAPI/Streaming/picture"
        ]

        for endpoint in endpoints:
            resp = await self._request("GET", endpoint)
            if resp and resp.status_code == 200 and resp.headers.get("content-type", "").startswith("image"):
                try:
                    image = Image.open(BytesIO(resp.content))
                    return np.array(image)
                except Exception as e:
                    logger.error(f"Failed to decode image: {e}")
                    continue

        logger.error(f"Failed to get snapshot from channel {channel_id}")
        return None

    async def get_event_stream(self):
        """
        Subscribe to camera events (ANPR, motion, etc.)
        Returns an async generator of events
        """
        # Use event notification stream
        endpoint = "/ISAPI/Event/notification/alertStream"

        try:
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream(
                    "GET",
                    f"{self.base_url}{endpoint}",
                    auth=self.auth
                ) as response:
                    buffer = b""
                    async for chunk in response.aiter_bytes():
                        buffer += chunk

                        # Parse multipart boundary events
                        while b"</EventNotificationAlert>" in buffer:
                            end_idx = buffer.find(b"</EventNotificationAlert>") + len(b"</EventNotificationAlert>")
                            event_data = buffer[:end_idx]
                            buffer = buffer[end_idx:]

                            event = self._parse_event(event_data)
                            if event:
                                yield event

        except Exception as e:
            logger.error(f"Event stream error: {e}")

    def _parse_event(self, data: bytes) -> Optional[Dict[str, Any]]:
        """Parse Hikvision event XML"""
        try:
            # Find XML content
            start = data.find(b"<EventNotificationAlert")
            if start == -1:
                return None

            xml_data = data[start:]
            root = ET.fromstring(xml_data)

            ns = {"hik": "http://www.hikvision.com/ver20/XMLSchema"}

            event = {
                "event_type": root.find("hik:eventType", ns).text if root.find("hik:eventType", ns) is not None else "unknown",
                "event_state": root.find("hik:eventState", ns).text if root.find("hik:eventState", ns) is not None else None,
                "channel_id": root.find("hik:channelID", ns).text if root.find("hik:channelID", ns) is not None else "1",
                "timestamp": root.find("hik:dateTime", ns).text if root.find("hik:dateTime", ns) is not None else None
            }

            # Parse ANPR (license plate) data if present
            anpr = root.find(".//hik:ANPR", ns)
            if anpr is not None:
                event["plate_number"] = anpr.find("hik:licensePlate", ns).text if anpr.find("hik:licensePlate", ns) is not None else None
                event["plate_confidence"] = float(anpr.find("hik:confidence", ns).text) if anpr.find("hik:confidence", ns) is not None else None

            return event

        except Exception as e:
            logger.error(f"Failed to parse event: {e}")
            return None

    async def control_gate(self, action: str = "open") -> bool:
        """
        Control access gate via camera's alarm output
        action: 'open' or 'close'
        """
        # Map action to alarm output state
        state = "active" if action == "open" else "inactive"

        # Try different alarm output endpoints
        endpoints = [
            "/ISAPI/System/IO/outputs/1/trigger",
            "/ISAPI/IO/outputs/1",
            "/ISAPI/AccessControl/RemoteControl/door/1"
        ]

        for endpoint in endpoints:
            if "trigger" in endpoint:
                # Simple trigger endpoint
                resp = await self._request("PUT", endpoint)
            elif "AccessControl" in endpoint:
                # Access control endpoint
                xml_body = f"""<?xml version="1.0" encoding="UTF-8"?>
                <RemoteControlDoor>
                    <cmd>{action}</cmd>
                </RemoteControlDoor>"""
                resp = await self._request(
                    "PUT",
                    endpoint,
                    content=xml_body,
                    headers={"Content-Type": "application/xml"}
                )
            else:
                # IO output endpoint
                xml_body = f"""<?xml version="1.0" encoding="UTF-8"?>
                <IOOutputPort>
                    <outputState>{state}</outputState>
                </IOOutputPort>"""
                resp = await self._request(
                    "PUT",
                    endpoint,
                    content=xml_body,
                    headers={"Content-Type": "application/xml"}
                )

            if resp and resp.status_code in (200, 204):
                logger.info(f"Gate {action} successful via {endpoint}")
                return True

        logger.error(f"Failed to {action} gate")
        return False

    async def get_device_info(self) -> Optional[Dict[str, Any]]:
        """Get device information"""
        resp = await self._request("GET", "/ISAPI/System/deviceInfo")
        if resp and resp.status_code == 200:
            try:
                root = ET.fromstring(resp.content)
                ns = {"hik": "http://www.hikvision.com/ver20/XMLSchema"}

                return {
                    "name": root.find("hik:deviceName", ns).text if root.find("hik:deviceName", ns) is not None else None,
                    "model": root.find("hik:model", ns).text if root.find("hik:model", ns) is not None else None,
                    "serial": root.find("hik:serialNumber", ns).text if root.find("hik:serialNumber", ns) is not None else None,
                    "firmware": root.find("hik:firmwareVersion", ns).text if root.find("hik:firmwareVersion", ns) is not None else None
                }
            except Exception as e:
                logger.error(f"Failed to parse device info: {e}")

        return None
