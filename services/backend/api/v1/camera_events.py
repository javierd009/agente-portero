"""Camera Events API - Hikvision camera event handling"""
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Header, Query
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select

from infrastructure.database import get_session
from domain.models import CameraEvent
from domain.models.camera_event import CameraEventCreate, CameraEventRead

router = APIRouter()


def get_tenant_id(x_tenant_id: UUID = Header(..., description="Tenant/Condominium ID")) -> UUID:
    return x_tenant_id


@router.get("/", response_model=List[CameraEventRead])
async def list_camera_events(
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
    skip: int = 0,
    limit: int = 100,
    event_type: Optional[str] = Query(None, description="Filter by type: plate_detected, face_detected, motion"),
    camera_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
):
    """List camera events for a condominium"""
    query = select(CameraEvent).where(CameraEvent.condominium_id == tenant_id)

    if event_type:
        query = query.where(CameraEvent.event_type == event_type)
    if camera_id:
        query = query.where(CameraEvent.camera_id == camera_id)
    if start_date:
        query = query.where(CameraEvent.created_at >= start_date)
    if end_date:
        query = query.where(CameraEvent.created_at <= end_date)

    query = query.order_by(CameraEvent.created_at.desc()).offset(skip).limit(limit)
    result = await session.execute(query)
    return result.scalars().all()


@router.post("/", response_model=CameraEventRead, status_code=201)
async def create_camera_event(
    event: CameraEventCreate,
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """Create a camera event (called by vision service)"""
    if event.condominium_id != tenant_id:
        raise HTTPException(status_code=403, detail="Cannot create event for different tenant")

    db_event = CameraEvent.model_validate(event)
    session.add(db_event)
    await session.commit()
    await session.refresh(db_event)
    return db_event


@router.get("/{event_id}", response_model=CameraEventRead)
async def get_camera_event(
    event_id: UUID,
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """Get a specific camera event"""
    query = select(CameraEvent).where(
        CameraEvent.id == event_id,
        CameraEvent.condominium_id == tenant_id
    )
    result = await session.execute(query)
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Camera event not found")
    return event


@router.post("/webhook/hikvision")
async def hikvision_webhook(
    event_data: dict,
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """
    Webhook endpoint for Hikvision camera events.
    Receives ISAPI event notifications and processes them.
    """
    # Parse Hikvision event format
    event_type = event_data.get("eventType", "unknown")
    camera_id = event_data.get("deviceID", event_data.get("channelID", "unknown"))

    # Extract plate if available
    plate = None
    if "ANPR" in event_type or "plate" in event_type.lower():
        plate = event_data.get("plateNumber") or event_data.get("licensePlate")

    # Create camera event record
    db_event = CameraEvent(
        condominium_id=tenant_id,
        camera_id=camera_id,
        event_type=event_type,
        plate_number=plate,
        metadata=event_data,
    )
    session.add(db_event)
    await session.commit()

    return {"status": "received", "event_id": str(db_event.id)}


@router.get("/plates/recent")
async def get_recent_plates(
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
    minutes: int = Query(5, description="Look back window in minutes"),
):
    """Get recently detected plates (for voice agent correlation)"""
    from datetime import timedelta

    cutoff = datetime.utcnow() - timedelta(minutes=minutes)
    query = select(CameraEvent).where(
        CameraEvent.condominium_id == tenant_id,
        CameraEvent.plate_number.isnot(None),
        CameraEvent.created_at >= cutoff
    ).order_by(CameraEvent.created_at.desc())

    result = await session.execute(query)
    events = result.scalars().all()

    return {
        "plates": [
            {"plate": e.plate_number, "timestamp": e.created_at, "camera_id": e.camera_id}
            for e in events
        ]
    }
