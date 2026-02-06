"""QrToken model - token record used to generate QR images/cards."""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID, uuid4

from sqlalchemy import JSON
from sqlmodel import SQLModel, Field, Column


class QrTokenBase(SQLModel):
    condominium_id: UUID = Field(foreign_key="condominiums.id", index=True)

    resident_id: Optional[UUID] = Field(foreign_key="residents.id", index=True, default=None)
    visitor_id: Optional[UUID] = Field(foreign_key="visitors.id", index=True, default=None)
    credential_id: Optional[UUID] = Field(foreign_key="access_credentials.id", index=True, default=None)

    token: str = Field(index=True)
    purpose: str = Field(default="visitor_access")
    allowed_access_points: List[str] = Field(default_factory=list, sa_column=Column(JSON))

    issued_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime

    used_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None

    max_uses: Optional[int] = None
    use_count: int = Field(default=0)

    metadata: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))


class QrToken(QrTokenBase, table=True):
    __tablename__ = "qr_tokens"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class QrTokenCreate(QrTokenBase):
    pass


class QrTokenRead(QrTokenBase):
    id: UUID
    created_at: datetime
