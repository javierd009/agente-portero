"""
Agente Portero - Vision Service
YOLO + PaddleOCR for plate and ID detection
Integrates with Hikvision cameras via ISAPI
"""
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from detector import PlateDetector
from hikvision import HikvisionClient
from event_processor import EventProcessor

# Configure logging
settings = get_settings()
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global instances
detector: PlateDetector = None
hikvision: HikvisionClient = None
event_processor: EventProcessor = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown"""
    global detector, hikvision, event_processor

    logger.info("Starting Vision Service...")

    # Initialize detector
    detector = PlateDetector(settings)
    await detector.initialize()

    # Initialize Hikvision client
    hikvision = HikvisionClient(settings)

    # Initialize event processor
    event_processor = EventProcessor(settings, detector, hikvision)

    # Start event listening
    asyncio.create_task(event_processor.start())

    logger.info("Vision Service started")

    yield

    # Shutdown
    logger.info("Stopping Vision Service...")
    if event_processor:
        await event_processor.stop()


app = FastAPI(
    title="Agente Portero Vision Service",
    description="YOLO + OCR for license plate and ID detection",
    version="0.1.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "vision-service",
        "detector_ready": detector.is_ready if detector else False
    }


@app.post("/detect/plate")
async def detect_plate_from_image(
    background_tasks: BackgroundTasks,
    image_url: str = None,
    camera_id: str = None
):
    """Detect license plate from image URL or camera snapshot"""
    if not detector or not detector.is_ready:
        return {"error": "Detector not ready"}

    # Get image
    if image_url:
        image = await detector.load_image_from_url(image_url)
    elif camera_id:
        image = await hikvision.get_snapshot(camera_id)
    else:
        return {"error": "Must provide image_url or camera_id"}

    if image is None:
        return {"error": "Failed to load image"}

    # Detect plate
    result = await detector.detect_plate(image)

    # Send to backend in background
    if result.get("plate"):
        background_tasks.add_task(
            event_processor.send_plate_event,
            camera_id or "api",
            result
        )

    return result


@app.post("/detect/id")
async def detect_id_from_image(
    image_url: str = None,
    camera_id: str = None
):
    """Detect ID card and extract text"""
    if not detector or not detector.is_ready:
        return {"error": "Detector not ready"}

    # Get image
    if image_url:
        image = await detector.load_image_from_url(image_url)
    elif camera_id:
        image = await hikvision.get_snapshot(camera_id)
    else:
        return {"error": "Must provide image_url or camera_id"}

    if image is None:
        return {"error": "Failed to load image"}

    # Detect ID
    result = await detector.detect_id(image)
    return result


@app.get("/cameras")
async def list_cameras():
    """List available cameras"""
    if not hikvision:
        return {"cameras": []}

    cameras = await hikvision.list_cameras()
    return {"cameras": cameras}


@app.post("/cameras/{camera_id}/snapshot")
async def get_camera_snapshot(camera_id: str):
    """Get snapshot from camera"""
    if not hikvision:
        return {"error": "Hikvision client not initialized"}

    snapshot = await hikvision.get_snapshot(camera_id)
    if snapshot:
        # Detect plate in snapshot
        result = await detector.detect_plate(snapshot)
        return result
    else:
        return {"error": "Failed to get snapshot"}


@app.post("/cameras/test")
async def test_camera(
    host: str = None,
    port: int = 80,
    username: str = None,
    password: str = None
):
    """
    Test camera connection - can test configured camera or custom camera
    If no parameters provided, tests the default configured camera
    """
    import httpx
    import xml.etree.ElementTree as ET

    # Use provided params or fall back to configured settings
    test_host = host or settings.hikvision_host
    test_port = port or settings.hikvision_port
    test_user = username or settings.hikvision_user
    test_pass = password or settings.hikvision_password

    if not test_host:
        return {"is_online": False, "error": "No camera host configured"}

    result = {
        "host": test_host,
        "port": test_port,
        "is_online": False,
        "device_info": None,
        "error": None
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            url = f"http://{test_host}:{test_port}/ISAPI/System/deviceInfo"
            response = await client.get(
                url,
                auth=httpx.DigestAuth(test_user, test_pass)
            )

            if response.status_code == 200:
                result["is_online"] = True
                # Parse device info
                try:
                    root = ET.fromstring(response.content)
                    ns = {"hik": "http://www.hikvision.com/ver20/XMLSchema"}
                    result["device_info"] = {
                        "name": root.find("hik:deviceName", ns).text if root.find("hik:deviceName", ns) is not None else None,
                        "model": root.find("hik:model", ns).text if root.find("hik:model", ns) is not None else None,
                        "serial": root.find("hik:serialNumber", ns).text if root.find("hik:serialNumber", ns) is not None else None,
                        "firmware": root.find("hik:firmwareVersion", ns).text if root.find("hik:firmwareVersion", ns) is not None else None
                    }
                except Exception as parse_error:
                    result["device_info"] = {"raw": response.text[:500]}
            elif response.status_code == 401:
                result["error"] = "Authentication failed - check username/password"
            else:
                result["error"] = f"HTTP {response.status_code}: {response.text[:200]}"

    except httpx.ConnectError:
        result["error"] = f"Cannot connect to {test_host}:{test_port} - check IP and network"
    except httpx.TimeoutException:
        result["error"] = f"Connection timeout to {test_host}:{test_port}"
    except Exception as e:
        result["error"] = str(e)

    return result


@app.get("/cameras/{camera_id}/snapshot/base64")
async def get_camera_snapshot_base64(camera_id: str):
    """Get snapshot from camera as base64 image"""
    import base64
    from io import BytesIO
    from PIL import Image

    if not hikvision:
        return {"error": "Hikvision client not initialized"}

    snapshot = await hikvision.get_snapshot(camera_id)
    if snapshot is not None:
        try:
            # Convert numpy array to base64
            img = Image.fromarray(snapshot)
            buffer = BytesIO()
            img.save(buffer, format="JPEG", quality=85)
            image_data = base64.b64encode(buffer.getvalue()).decode()
            return {
                "camera_id": camera_id,
                "image": f"data:image/jpeg;base64,{image_data}",
                "success": True
            }
        except Exception as e:
            return {"error": f"Failed to encode image: {str(e)}", "success": False}
    else:
        return {"error": "Failed to get snapshot from camera", "success": False}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.service_port,
        reload=settings.debug
    )
