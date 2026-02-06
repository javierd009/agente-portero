"""
Plate and ID Detector using YOLO + PaddleOCR
"""
import asyncio
import logging
from typing import Optional, Dict, Any, List, Tuple
import numpy as np
from io import BytesIO

import httpx
from PIL import Image

from config import Settings

logger = logging.getLogger(__name__)


class PlateDetector:
    """License plate and ID card detector using YOLO + OCR"""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.yolo_model = None
        self.ocr = None
        self.is_ready = False

    async def initialize(self):
        """Initialize YOLO and OCR models"""
        logger.info("Initializing detection models...")

        # Run in executor to avoid blocking
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._load_models)

        self.is_ready = True
        logger.info("Detection models initialized")

    def _load_models(self):
        """Load YOLO and PaddleOCR models (blocking)"""
        try:
            # Load YOLO
            from ultralytics import YOLO
            self.yolo_model = YOLO(self.settings.yolo_model)
            logger.info(f"YOLO model loaded: {self.settings.yolo_model}")
        except Exception as e:
            logger.error(f"Failed to load YOLO model: {e}")
            # Continue without YOLO, will use OCR directly

        try:
            # Load PaddleOCR
            from paddleocr import PaddleOCR
            self.ocr = PaddleOCR(
                use_angle_cls=True,
                lang=self.settings.ocr_language,
                use_gpu=False,  # Set to True if CUDA available
                show_log=False
            )
            logger.info("PaddleOCR loaded")
        except Exception as e:
            logger.error(f"Failed to load PaddleOCR: {e}")

    async def load_image_from_url(self, url: str) -> Optional[np.ndarray]:
        """Load image from URL"""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, timeout=10)
                if resp.status_code == 200:
                    image = Image.open(BytesIO(resp.content))
                    return np.array(image)
        except Exception as e:
            logger.error(f"Failed to load image from URL: {e}")
        return None

    async def detect_plate(self, image: np.ndarray) -> Dict[str, Any]:
        """Detect license plate in image"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._detect_plate_sync, image)

    def _detect_plate_sync(self, image: np.ndarray) -> Dict[str, Any]:
        """Synchronous plate detection"""
        result = {
            "plate": None,
            "confidence": 0.0,
            "bbox": None,
            "raw_detections": []
        }

        try:
            # If YOLO is available, detect plate region first
            plate_region = image
            if self.yolo_model:
                detections = self.yolo_model(image, conf=self.settings.yolo_confidence)

                for det in detections:
                    boxes = det.boxes
                    for box in boxes:
                        # Look for vehicle/plate class
                        cls = int(box.cls[0])
                        conf = float(box.conf[0])

                        # YOLO class 2 is 'car', we can also train custom model for plates
                        if cls in [2, 5, 7]:  # car, bus, truck
                            x1, y1, x2, y2 = map(int, box.xyxy[0])
                            # Crop to likely plate region (bottom portion of vehicle)
                            h = y2 - y1
                            plate_y1 = y1 + int(h * 0.6)  # Bottom 40% of vehicle
                            plate_region = image[plate_y1:y2, x1:x2]
                            result["bbox"] = [x1, plate_y1, x2, y2]
                            break

            # Run OCR on plate region
            if self.ocr and plate_region.size > 0:
                ocr_result = self.ocr.ocr(plate_region, cls=True)

                if ocr_result and ocr_result[0]:
                    # Find text that looks like a license plate
                    for line in ocr_result[0]:
                        text = line[1][0]
                        confidence = line[1][1]

                        # Mexican plate format: ABC-12-34 or ABC-123-A
                        cleaned = self._clean_plate_text(text)

                        if self._is_valid_plate(cleaned):
                            if confidence > result["confidence"]:
                                result["plate"] = cleaned
                                result["confidence"] = confidence

                        result["raw_detections"].append({
                            "text": text,
                            "cleaned": cleaned,
                            "confidence": confidence
                        })

        except Exception as e:
            logger.error(f"Plate detection error: {e}")
            result["error"] = str(e)

        return result

    def _clean_plate_text(self, text: str) -> str:
        """Clean and normalize plate text"""
        # Remove common OCR errors and normalize
        text = text.upper()
        text = text.replace(" ", "").replace("-", "").replace(".", "")
        text = text.replace("O", "0").replace("I", "1").replace("S", "5")
        text = text.replace("B", "8").replace("G", "6")

        # Keep only alphanumeric
        text = "".join(c for c in text if c.isalnum())

        # Format as Mexican plate
        if len(text) >= 6:
            # Try ABC-12-34 format
            if len(text) == 7:
                return f"{text[:3]}-{text[3:5]}-{text[5:]}"
            elif len(text) == 6:
                return f"{text[:3]}-{text[3:]}"

        return text

    def _is_valid_plate(self, text: str) -> bool:
        """Check if text looks like a valid Mexican license plate"""
        # Remove dashes for validation
        clean = text.replace("-", "")

        if len(clean) < 5 or len(clean) > 8:
            return False

        # Should have mix of letters and numbers
        has_letters = any(c.isalpha() for c in clean)
        has_numbers = any(c.isdigit() for c in clean)

        return has_letters and has_numbers

    async def detect_id(self, image: np.ndarray) -> Dict[str, Any]:
        """Detect ID card and extract information"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._detect_id_sync, image)

    def _detect_id_sync(self, image: np.ndarray) -> Dict[str, Any]:
        """Synchronous ID detection"""
        result = {
            "id_number": None,
            "name": None,
            "all_text": [],
            "confidence": 0.0
        }

        try:
            if not self.ocr:
                result["error"] = "OCR not available"
                return result

            ocr_result = self.ocr.ocr(image, cls=True)

            if ocr_result and ocr_result[0]:
                all_text = []

                for line in ocr_result[0]:
                    text = line[1][0]
                    confidence = line[1][1]
                    all_text.append({"text": text, "confidence": confidence})

                    # Look for ID patterns
                    # Mexican INE/IFE: IDMEX followed by numbers
                    if "IDMEX" in text.upper() or self._looks_like_id_number(text):
                        cleaned = "".join(c for c in text if c.isdigit())
                        if len(cleaned) >= 10:
                            result["id_number"] = cleaned
                            result["confidence"] = confidence

                    # Look for name patterns (usually APELLIDO, NOMBRE format)
                    if text.isupper() and len(text) > 5 and text.isalpha():
                        if not result["name"]:
                            result["name"] = text

                result["all_text"] = all_text

        except Exception as e:
            logger.error(f"ID detection error: {e}")
            result["error"] = str(e)

        return result

    def _looks_like_id_number(self, text: str) -> bool:
        """Check if text looks like an ID number"""
        digits = sum(1 for c in text if c.isdigit())
        return digits >= 8
