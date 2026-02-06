"""
Event Processor
Handles camera events and sends detection results to backend
"""
import asyncio
import logging
from typing import Dict, Any, Optional

import httpx

from config import Settings
from detector import PlateDetector
from hikvision import HikvisionClient

logger = logging.getLogger(__name__)


class EventProcessor:
    """Processes camera events and coordinates detection"""

    def __init__(
        self,
        settings: Settings,
        detector: PlateDetector,
        hikvision: HikvisionClient
    ):
        self.settings = settings
        self.detector = detector
        self.hikvision = hikvision
        self.running = False
        self.tenant_id: Optional[str] = None  # Set from config or API

    async def start(self):
        """Start processing camera events"""
        self.running = True
        logger.info("Event processor started")

        # Start listening to Hikvision event stream
        asyncio.create_task(self._listen_camera_events())

    async def stop(self):
        """Stop event processor"""
        self.running = False
        logger.info("Event processor stopped")

    async def _listen_camera_events(self):
        """Listen for camera events and process them"""
        while self.running:
            try:
                async for event in self.hikvision.get_event_stream():
                    if not self.running:
                        break

                    await self._process_camera_event(event)

            except Exception as e:
                logger.error(f"Camera event stream error: {e}")
                await asyncio.sleep(5)  # Reconnect delay

    async def _process_camera_event(self, event: Dict[str, Any]):
        """Process a single camera event"""
        event_type = event.get("event_type", "").lower()
        channel_id = event.get("channel_id", "1")

        logger.info(f"Camera event: {event_type} on channel {channel_id}")

        # If camera provides plate directly (ANPR cameras)
        if event.get("plate_number"):
            await self.send_plate_event(channel_id, {
                "plate": event["plate_number"],
                "confidence": event.get("plate_confidence", 0.9),
                "source": "camera_anpr"
            })
            return

        # For motion/line crossing events, capture and analyze
        if event_type in ["motion", "linedetection", "fielddetection", "vmd"]:
            # Get snapshot and detect
            image = await self.hikvision.get_snapshot(channel_id)
            if image is not None:
                result = await self.detector.detect_plate(image)
                if result.get("plate"):
                    result["source"] = "vision_service"
                    await self.send_plate_event(channel_id, result)

    async def send_plate_event(
        self,
        camera_id: str,
        detection: Dict[str, Any]
    ):
        """Send plate detection event to backend"""
        try:
            async with httpx.AsyncClient() as client:
                event_data = {
                    "camera_id": camera_id,
                    "event_type": "plate_detected",
                    "plate_number": detection.get("plate"),
                    "plate_confidence": detection.get("confidence"),
                    "metadata": {
                        "source": detection.get("source", "vision_service"),
                        "raw_detections": detection.get("raw_detections", [])
                    }
                }

                headers = {}
                if self.tenant_id:
                    headers["X-Tenant-ID"] = self.tenant_id
                    event_data["condominium_id"] = self.tenant_id

                resp = await client.post(
                    f"{self.settings.backend_api_url}/api/v1/camera-events/",
                    json=event_data,
                    headers=headers,
                    timeout=10
                )

                if resp.status_code == 201:
                    logger.info(f"Plate event sent: {detection.get('plate')}")
                else:
                    logger.error(f"Failed to send plate event: {resp.status_code}")

        except Exception as e:
            logger.error(f"Error sending plate event: {e}")

    async def send_id_event(
        self,
        camera_id: str,
        detection: Dict[str, Any]
    ):
        """Send ID detection event to backend"""
        try:
            async with httpx.AsyncClient() as client:
                event_data = {
                    "camera_id": camera_id,
                    "event_type": "id_detected",
                    "metadata": {
                        "id_number": detection.get("id_number"),
                        "name": detection.get("name"),
                        "confidence": detection.get("confidence"),
                        "all_text": detection.get("all_text", [])
                    }
                }

                headers = {}
                if self.tenant_id:
                    headers["X-Tenant-ID"] = self.tenant_id
                    event_data["condominium_id"] = self.tenant_id

                resp = await client.post(
                    f"{self.settings.backend_api_url}/api/v1/camera-events/",
                    json=event_data,
                    headers=headers,
                    timeout=10
                )

                if resp.status_code == 201:
                    logger.info(f"ID event sent: {detection.get('id_number')}")
                else:
                    logger.error(f"Failed to send ID event: {resp.status_code}")

        except Exception as e:
            logger.error(f"Error sending ID event: {e}")


class PeriodicScanner:
    """
    Periodically scans cameras for plates
    Useful when event streaming is not available
    """

    def __init__(
        self,
        settings: Settings,
        detector: PlateDetector,
        hikvision: HikvisionClient,
        event_processor: EventProcessor,
        interval_seconds: int = 5
    ):
        self.settings = settings
        self.detector = detector
        self.hikvision = hikvision
        self.event_processor = event_processor
        self.interval = interval_seconds
        self.running = False
        self.last_plates: Dict[str, str] = {}  # camera_id -> last plate

    async def start(self):
        """Start periodic scanning"""
        self.running = True
        logger.info(f"Periodic scanner started (interval: {self.interval}s)")

        while self.running:
            try:
                cameras = await self.hikvision.list_cameras()

                for camera in cameras:
                    if not camera.get("enabled"):
                        continue

                    camera_id = camera.get("id", "1")
                    image = await self.hikvision.get_snapshot(camera_id)

                    if image is not None:
                        result = await self.detector.detect_plate(image)

                        if result.get("plate"):
                            plate = result["plate"]

                            # Only send if different from last detection
                            if plate != self.last_plates.get(camera_id):
                                self.last_plates[camera_id] = plate
                                result["source"] = "periodic_scan"
                                await self.event_processor.send_plate_event(
                                    camera_id,
                                    result
                                )

            except Exception as e:
                logger.error(f"Periodic scan error: {e}")

            await asyncio.sleep(self.interval)

    async def stop(self):
        """Stop periodic scanning"""
        self.running = False
