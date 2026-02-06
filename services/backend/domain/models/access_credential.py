"""AccessCredential model - generic credential layer (QR now, scalable to PIN/plate/face/card)."""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID, uuid4

from sqlalchemy import JSON
from sqlmodel import SQLModel, Field, Column


class AccessCredentialBase(SQLModel):
    condominium_id: UUID = Field(foreign_key="condominiums.id", index=True)

    resident_id: Optional[UUID] = Field(foreign_key="residents.id", index=True, default=None)
    visitor_id: Optional[UUID] = Field(foreign_key="visitors.id", index=True, default=None)

    credential_type: str  # qr | pin | plate | face | card

    allowed_access_points: List[str] = Field(default_factory=list, sa_column=Column(JSON))

    valid_from: datetime = Field(default_factory=datetime.utcnow)
    valid_until: Optional[datetime] = None

    status: str = Field(default="active")  # active | used | revoked | expired
    used_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None

    # Usage limits
    max_uses: Optional[int] = None  # NULL=unlimited within window; 1=single-use; N=N uses
    use_count: int = Field(default=0)

    provisioning_mode: str = Field(default="backend")  # backend | device
    device_target: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))

    metadata: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))


class AccessCredential(AccessCredentialBase, table=True):
    __tablename__ = "access_credentials"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class AccessCredentialCreate(AccessCredentialBase):
    pass


class AccessCredentialRead(AccessCredentialBase):
    id: UUID
    created_at: datetime
    updated_at: datetime


class AccessCredentialUpdate(SQLModel):
    status: Optional[str] = None
    used_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    max_uses: Optional[int] = None
    use_count: Optional[int] = None
    allowed_access_points: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
