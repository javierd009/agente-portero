"""Visitor model"""
from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field
from uuid import UUID, uuid4

class VisitorBase(SQLModel):
    condominium_id: UUID = Field(foreign_key="condominiums.id", index=True)
    resident_id: Optional[UUID] = Field(foreign_key="residents.id", index=True, default=None)
    name: str
    id_number: Optional[str] = None  # Cedula/ID
    phone: Optional[str] = None
    vehicle_plate: Optional[str] = None
    reason: Optional[str] = None
    notes: Optional[str] = None  # Additional notes
    authorized_by: Optional[str] = None  # 'resident', 'guard', 'ai_agent', 'whatsapp'
    valid_until: Optional[datetime] = None  # For temporary authorizations
    entry_time: Optional[datetime] = None
    exit_time: Optional[datetime] = None
    status: str = Field(default="pending")  # pending, approved, denied, inside, exited

class Visitor(VisitorBase, table=True):
    __tablename__ = "visitors"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class VisitorCreate(VisitorBase):
    pass

class VisitorRead(VisitorBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

class VisitorUpdate(SQLModel):
    name: Optional[str] = None
    id_number: Optional[str] = None
    phone: Optional[str] = None
    vehicle_plate: Optional[str] = None
    reason: Optional[str] = None
    notes: Optional[str] = None
    authorized_by: Optional[str] = None
    valid_until: Optional[datetime] = None
    entry_time: Optional[datetime] = None
    exit_time: Optional[datetime] = None
    status: Optional[str] = None
