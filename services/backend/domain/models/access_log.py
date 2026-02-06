"""Access Log model - Physical access events"""
from typing import Optional, Dict, Any
from datetime import datetime
from sqlmodel import SQLModel, Field, Column
from sqlalchemy import JSON
from uuid import UUID, uuid4


class AccessLogBase(SQLModel):
    condominium_id: UUID = Field(foreign_key="condominiums.id", index=True)
    event_type: str = Field(index=True)  # 'entry', 'exit', 'denied', 'visitor_entry'
    access_point: str  # 'main_gate', 'pedestrian_gate', 'parking'
    direction: Optional[str] = None  # 'in', 'out'

    # Who/What
    resident_id: Optional[UUID] = Field(foreign_key="residents.id", default=None)
    visitor_id: Optional[UUID] = Field(foreign_key="visitors.id", default=None)
    visitor_name: Optional[str] = None
    vehicle_plate: Optional[str] = Field(index=True, default=None)

    # Authorization
    authorization_method: str  # 'auto_plate', 'manual_guard', 'ai_agent', 'resident_app'
    authorized_by: Optional[UUID] = None  # User who authorized (if manual)

    # Evidence
    camera_snapshot_url: Optional[str] = None
    confidence_score: Optional[float] = None  # For AI-based authorization

    extra_data: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))


class AccessLog(AccessLogBase, table=True):
    __tablename__ = "access_logs"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class AccessLogCreate(AccessLogBase):
    pass

class AccessLogRead(AccessLogBase):
    id: UUID
    created_at: datetime
