"""AuditLog model - append-only audit trail for actions (agent/operator/resident)."""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID, uuid4

from sqlalchemy import JSON
from sqlmodel import SQLModel, Field, Column


class AuditLogBase(SQLModel):
    condominium_id: UUID = Field(foreign_key="condominiums.id", index=True)

    actor_type: str  # resident | operator | agent | api_key
    actor_id: Optional[str] = None
    actor_label: Optional[str] = None

    action: str  # issue_qr | revoke_credential | open_gate | etc.
    resource_type: Optional[str] = None
    resource_id: Optional[UUID] = None

    status: str = Field(default="success")  # success | failure
    message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))


class AuditLog(AuditLogBase, table=True):
    __tablename__ = "audit_logs"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AuditLogCreate(AuditLogBase):
    pass


class AuditLogRead(AuditLogBase):
    id: UUID
    created_at: datetime
