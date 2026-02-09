"""Telephony extension mapping (FreePBX/intercom) -> access action."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import SQLModel, Field


class TelephonyExtensionBase(SQLModel):
    condominium_id: UUID = Field(foreign_key="condominiums.id", index=True)

    extension: str = Field(index=True)
    access_point: str

    device_type: str  # panel | biometric
    device_host: str
    door_id: int = 1

    enabled: bool = True


class TelephonyExtension(TelephonyExtensionBase, table=True):
    __tablename__ = "tenant_telephony_extensions"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class TelephonyExtensionCreate(TelephonyExtensionBase):
    pass


class TelephonyExtensionRead(TelephonyExtensionBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
