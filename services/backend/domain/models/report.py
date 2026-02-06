"""Report model - Incident/maintenance reports"""
from typing import Optional, Dict, Any
from datetime import datetime
from sqlmodel import SQLModel, Field, Column
from sqlalchemy import JSON
from uuid import UUID, uuid4


class ReportBase(SQLModel):
    condominium_id: UUID = Field(foreign_key="condominiums.id", index=True)
    resident_id: Optional[UUID] = Field(foreign_key="residents.id", index=True, default=None)

    report_type: str = Field(index=True)  # 'maintenance', 'security', 'noise', 'cleaning', 'other'
    title: str
    description: str
    location: Optional[str] = None
    urgency: str = Field(default="normal")  # 'low', 'normal', 'high', 'urgent'

    # Status tracking
    status: str = Field(default="pending", index=True)  # pending, in_progress, resolved, closed
    assigned_to: Optional[UUID] = None  # Admin/staff assigned
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None

    # Source
    source: str = Field(default="web")  # 'web', 'whatsapp', 'voice', 'email'

    # Attachments
    photo_urls: Optional[Dict[str, Any]] = Field(default_factory=dict, sa_column=Column(JSON))
    extra_data: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))


class Report(ReportBase, table=True):
    __tablename__ = "reports"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ReportCreate(ReportBase):
    pass


class ReportRead(ReportBase):
    id: UUID
    created_at: datetime
    updated_at: datetime


class ReportUpdate(SQLModel):
    title: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    urgency: Optional[str] = None
    status: Optional[str] = None
    assigned_to: Optional[UUID] = None
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None
    photo_urls: Optional[Dict[str, Any]] = None
    extra_data: Optional[Dict[str, Any]] = None
