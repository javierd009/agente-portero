"""Camera model - Hikvision camera configuration"""
from typing import Optional, Dict, Any
from datetime import datetime
from sqlmodel import SQLModel, Field, Column
from sqlalchemy import JSON
from uuid import UUID, uuid4


class CameraBase(SQLModel):
    condominium_id: UUID = Field(foreign_key="condominiums.id", index=True)
    name: str = Field(max_length=100)
    location: Optional[str] = Field(max_length=200, default=None)

    # Connection
    host: str = Field(max_length=255)
    port: int = Field(default=80)
    username: str = Field(max_length=100)
    password: str = Field(max_length=255)  # Should be encrypted in production

    # Camera type and capabilities
    camera_type: str = Field(default="hikvision")  # 'hikvision', 'dahua', 'generic'
    has_ptz: bool = Field(default=False)
    has_anpr: bool = Field(default=False)  # Automatic Number Plate Recognition
    has_face: bool = Field(default=False)  # Face detection

    # Stream URLs (auto-generated or manual)
    rtsp_main: Optional[str] = None
    rtsp_sub: Optional[str] = None
    snapshot_url: Optional[str] = None

    # Status
    is_active: bool = Field(default=True)
    is_online: bool = Field(default=False)
    last_seen: Optional[datetime] = None

    # Settings
    settings: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))


class Camera(CameraBase, table=True):
    __tablename__ = "cameras"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class CameraCreate(SQLModel):
    condominium_id: UUID
    name: str
    location: Optional[str] = None
    host: str
    port: int = 80
    username: str
    password: str
    camera_type: str = "hikvision"
    has_ptz: bool = False
    has_anpr: bool = False
    has_face: bool = False


class CameraUpdate(SQLModel):
    name: Optional[str] = None
    location: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None
    has_ptz: Optional[bool] = None
    has_anpr: Optional[bool] = None
    has_face: Optional[bool] = None


class CameraRead(CameraBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        # Hide password in responses
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "Entrada Principal",
                "host": "192.168.1.100"
            }
        }


class CameraReadPublic(SQLModel):
    """Public camera info without sensitive data"""
    id: UUID
    condominium_id: UUID
    name: str
    location: Optional[str]
    camera_type: str
    has_ptz: bool
    has_anpr: bool
    has_face: bool
    is_active: bool
    is_online: bool
    last_seen: Optional[datetime]
    created_at: datetime
