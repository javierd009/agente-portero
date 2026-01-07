"""Camera Event model - Events from vision service"""
from typing import Optional, Dict, Any
from datetime import datetime
from sqlmodel import SQLModel, Field, Column
from sqlalchemy import JSON
from uuid import UUID, uuid4


class CameraEventBase(SQLModel):
    condominium_id: UUID = Field(foreign_key="condominiums.id", index=True)
    camera_id: str = Field(index=True)
    event_type: str = Field(index=True)  # 'plate_detected', 'face_detected', 'motion', 'person'

    # Detection results
    plate_number: Optional[str] = Field(index=True, default=None)
    plate_confidence: Optional[float] = None
    face_id: Optional[str] = None
    face_confidence: Optional[float] = None

    # Evidence
    snapshot_url: Optional[str] = None
    video_clip_url: Optional[str] = None

    # Processing
    processed: bool = Field(default=False)
    matched_resident_id: Optional[UUID] = Field(foreign_key="residents.id", default=None)
    matched_vehicle_id: Optional[UUID] = Field(foreign_key="vehicles.id", default=None)

    extra_data: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))

class CameraEvent(CameraEventBase, table=True):
    __tablename__ = "camera_events"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class CameraEventCreate(CameraEventBase):
    pass

class CameraEventRead(CameraEventBase):
    id: UUID
    created_at: datetime
