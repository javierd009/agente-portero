"""Cameras API - Camera management and VMS functionality"""
import os
import logging
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
import httpx

from infrastructure.database import get_session
from domain.models.camera import Camera, CameraCreate, CameraRead, CameraReadPublic, CameraUpdate

router = APIRouter()
logger = logging.getLogger(__name__)

# Vision service URL for proxying camera requests (on-premise)
# When set, camera test/snapshot requests will go through vision-service
# Example: http://integrateccr.ddns.net:8001
VISION_SERVICE_URL = os.getenv("VISION_SERVICE_URL", "")


def get_tenant_id(x_tenant_id: UUID = Header(..., description="Tenant/Condominium ID")) -> UUID:
    """Extract tenant ID from header for multi-tenant isolation"""
    return x_tenant_id


# ==========================================
# Vision Service Proxy Endpoints (MUST be before /{camera_id} routes)
# These allow the dashboard to communicate with the vision-service
# through the backend, avoiding HTTPS/HTTP mixed content issues
# ==========================================

@router.get("/vision-service/health")
async def vision_service_health(
    vision_url: str,
):
    """Proxy health check to vision-service (avoids mixed content)"""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(f"{vision_url}/health")
            if response.status_code == 200:
                return response.json()
            return {"status": "error", "code": response.status_code}
    except httpx.ConnectError:
        return {"status": "offline", "error": "Cannot connect to vision service"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.post("/vision-service/test-camera")
async def vision_service_test_camera(
    vision_url: str,
    host: str,
    port: int = 80,
    username: str = "admin",
    password: str = "",
):
    """Proxy camera test to vision-service"""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                f"{vision_url}/cameras/test",
                params={
                    "host": host,
                    "port": port,
                    "username": username,
                    "password": password
                }
            )
            return response.json()
    except httpx.ConnectError:
        return {"is_online": False, "error": "Cannot connect to vision service"}
    except Exception as e:
        return {"is_online": False, "error": str(e)}


@router.get("/vision-service/snapshot")
async def vision_service_snapshot(
    vision_url: str,
    channel_id: str = "1",
):
    """Proxy snapshot request to vision-service"""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(f"{vision_url}/cameras/{channel_id}/snapshot/base64")
            return response.json()
    except httpx.ConnectError:
        return {"success": False, "error": "Cannot connect to vision service"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ==========================================
# Camera CRUD Endpoints
# ==========================================

@router.get("/", response_model=List[CameraReadPublic])
async def list_cameras(
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
    skip: int = 0,
    limit: int = 100,
    is_active: Optional[bool] = None,
):
    """List all cameras for a condominium"""
    query = select(Camera).where(Camera.condominium_id == tenant_id)

    if is_active is not None:
        query = query.where(Camera.is_active == is_active)

    query = query.offset(skip).limit(limit)
    result = await session.execute(query)
    return result.scalars().all()


@router.post("/", response_model=CameraReadPublic, status_code=201)
async def create_camera(
    camera: CameraCreate,
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """Add a new camera to the condominium"""
    if camera.condominium_id != tenant_id:
        raise HTTPException(status_code=403, detail="Cannot create camera for different tenant")

    # Generate RTSP URLs based on camera type
    db_camera = Camera.model_validate(camera)

    if camera.camera_type == "hikvision":
        db_camera.rtsp_main = f"rtsp://{camera.username}:{camera.password}@{camera.host}:{camera.port}/Streaming/Channels/101"
        db_camera.rtsp_sub = f"rtsp://{camera.username}:{camera.password}@{camera.host}:{camera.port}/Streaming/Channels/102"
        db_camera.snapshot_url = f"http://{camera.host}:{camera.port}/ISAPI/Streaming/channels/101/picture"

    session.add(db_camera)
    await session.commit()
    await session.refresh(db_camera)
    return db_camera


@router.get("/{camera_id}", response_model=CameraRead)
async def get_camera(
    camera_id: UUID,
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """Get a specific camera by ID"""
    query = select(Camera).where(
        Camera.id == camera_id,
        Camera.condominium_id == tenant_id
    )
    result = await session.execute(query)
    camera = result.scalar_one_or_none()

    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")

    return camera


@router.patch("/{camera_id}", response_model=CameraReadPublic)
async def update_camera(
    camera_id: UUID,
    camera_update: CameraUpdate,
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """Update a camera"""
    query = select(Camera).where(
        Camera.id == camera_id,
        Camera.condominium_id == tenant_id
    )
    result = await session.execute(query)
    db_camera = result.scalar_one_or_none()

    if not db_camera:
        raise HTTPException(status_code=404, detail="Camera not found")

    update_data = camera_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_camera, key, value)

    # Regenerate RTSP URLs if connection details changed
    if any(k in update_data for k in ['host', 'port', 'username', 'password']):
        if db_camera.camera_type == "hikvision":
            db_camera.rtsp_main = f"rtsp://{db_camera.username}:{db_camera.password}@{db_camera.host}:{db_camera.port}/Streaming/Channels/101"
            db_camera.rtsp_sub = f"rtsp://{db_camera.username}:{db_camera.password}@{db_camera.host}:{db_camera.port}/Streaming/Channels/102"
            db_camera.snapshot_url = f"http://{db_camera.host}:{db_camera.port}/ISAPI/Streaming/channels/101/picture"

    session.add(db_camera)
    await session.commit()
    await session.refresh(db_camera)
    return db_camera


@router.delete("/{camera_id}", status_code=204)
async def delete_camera(
    camera_id: UUID,
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """Delete a camera"""
    query = select(Camera).where(
        Camera.id == camera_id,
        Camera.condominium_id == tenant_id
    )
    result = await session.execute(query)
    camera = result.scalar_one_or_none()

    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")

    await session.delete(camera)
    await session.commit()
    return None


@router.post("/{camera_id}/test")
async def test_camera_connection(
    camera_id: UUID,
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """Test camera connection and update status"""
    query = select(Camera).where(
        Camera.id == camera_id,
        Camera.condominium_id == tenant_id
    )
    result = await session.execute(query)
    camera = result.scalar_one_or_none()

    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")

    # Try to connect to camera
    is_online = False
    device_info = None

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            # If vision service is configured, proxy the request through it
            # (vision-service runs on-premise and can reach local cameras)
            if VISION_SERVICE_URL:
                logger.info(f"Testing camera via vision-service: {VISION_SERVICE_URL}")
                response = await client.post(
                    f"{VISION_SERVICE_URL}/cameras/test",
                    params={
                        "host": camera.host,
                        "port": camera.port,
                        "username": camera.username,
                        "password": camera.password
                    }
                )
                if response.status_code == 200:
                    data = response.json()
                    is_online = data.get("is_online", False)
                    device_info = data.get("device_info") or {"status": "connected via vision-service"}
                    if data.get("error"):
                        device_info = {"status": "error", "error": data["error"]}
                else:
                    device_info = {"status": "error", "error": f"Vision service error: {response.status_code}"}
            else:
                # Direct connection (only works when backend and camera are on same network)
                if camera.camera_type == "hikvision":
                    url = f"http://{camera.host}:{camera.port}/ISAPI/System/deviceInfo"
                    response = await client.get(
                        url,
                        auth=httpx.DigestAuth(camera.username, camera.password)
                    )
                    is_online = response.status_code == 200
                    if is_online:
                        device_info = {"status": "connected", "raw": response.text[:500]}
    except httpx.ConnectError as e:
        if VISION_SERVICE_URL:
            device_info = {"status": "error", "error": f"Cannot connect to vision-service at {VISION_SERVICE_URL}"}
        else:
            device_info = {"status": "error", "error": f"Cannot connect to camera: {str(e)}"}
    except Exception as e:
        device_info = {"status": "error", "error": str(e)}

    # Update camera status
    camera.is_online = is_online
    if is_online:
        camera.last_seen = datetime.utcnow()

    session.add(camera)
    await session.commit()

    return {
        "camera_id": str(camera_id),
        "is_online": is_online,
        "device_info": device_info
    }


@router.get("/{camera_id}/snapshot")
async def get_camera_snapshot(
    camera_id: UUID,
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """Get current snapshot from camera"""
    query = select(Camera).where(
        Camera.id == camera_id,
        Camera.condominium_id == tenant_id
    )
    result = await session.execute(query)
    camera = result.scalar_one_or_none()

    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            # If vision service is configured, proxy through it
            if VISION_SERVICE_URL:
                logger.info(f"Getting snapshot via vision-service: {VISION_SERVICE_URL}")
                # Vision service uses channel ID "1" for main stream
                response = await client.get(f"{VISION_SERVICE_URL}/cameras/1/snapshot/base64")
                if response.status_code == 200:
                    data = response.json()
                    if data.get("success") and data.get("image"):
                        return {
                            "camera_id": str(camera_id),
                            "image": data["image"],
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    else:
                        raise HTTPException(status_code=500, detail=data.get("error", "Failed to get snapshot"))
                else:
                    raise HTTPException(status_code=500, detail=f"Vision service error: {response.status_code}")
            else:
                # Direct connection
                if camera.camera_type == "hikvision":
                    url = f"http://{camera.host}:{camera.port}/ISAPI/Streaming/channels/101/picture"
                    response = await client.get(
                        url,
                        auth=httpx.DigestAuth(camera.username, camera.password)
                    )
                    if response.status_code == 200:
                        import base64
                        image_data = base64.b64encode(response.content).decode()
                        return {
                            "camera_id": str(camera_id),
                            "image": f"data:image/jpeg;base64,{image_data}",
                            "timestamp": datetime.utcnow().isoformat()
                        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get snapshot: {str(e)}")

    raise HTTPException(status_code=500, detail="Failed to get snapshot from camera")
