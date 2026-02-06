"""Audit/bitácora endpoints.

These endpoints are intended for internal services (e.g., WhatsApp fast-path)
that need to write deterministic, low-latency audit logs.

Auth/RBAC: for now this is protected by the gateway layer / network boundary.
Later we can enforce a signed service token.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, Field
from sqlmodel.ext.asyncio.session import AsyncSession

from infrastructure.database import get_session
from domain.models.audit_log import AuditLog
from domain.models.access_log import AccessLog

router = APIRouter()

AccessPoint = Literal["vehicular_entry", "vehicular_exit", "pedestrian"]


def get_tenant_id(x_tenant_id: UUID = Header(..., description="Tenant/Condominium ID")) -> UUID:
    return x_tenant_id


class LogOpenRequest(BaseModel):
    access_point: AccessPoint
    success: bool = True

    # actor context
    actor_channel: str = Field(default="whatsapp")
    actor_phone: Optional[str] = None
    message_id: Optional[str] = None
    resident_id: Optional[UUID] = None

    # optional device context (do NOT show to users, but OK for internal logs)
    device_host: Optional[str] = None
    door_id: Optional[int] = None
    method: Optional[str] = None


class LogOpenResponse(BaseModel):
    logged: bool
    audit_id: UUID
    access_log_id: UUID


@router.post("/log-open", response_model=LogOpenResponse)
async def log_open(
    req: LogOpenRequest,
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    now = datetime.utcnow()

    access_log = AccessLog(
        condominium_id=tenant_id,
        event_type="open_gate",
        access_point=req.access_point,
        direction=None,
        resident_id=req.resident_id,
        visitor_id=None,
        visitor_name=None,
        vehicle_plate=None,
        authorization_method=req.actor_channel,
        authorized_by=req.actor_phone,
        camera_snapshot_url=None,
        confidence_score=None,
        extra_data={
            "success": req.success,
            "message_id": req.message_id,
            "device_host": req.device_host,
            "door_id": req.door_id,
            "method": req.method,
        },
        created_at=now,
    )
    session.add(access_log)
    await session.flush()

    audit = AuditLog(
        condominium_id=tenant_id,
        actor_type=req.actor_channel,
        actor_id=req.actor_phone,
        actor_label=None,
        action="open_gate",
        resource_type="access_point",
        resource_id=None,
        status="success" if req.success else "failure",
        message=f"open {req.access_point}",
        extra_data={
            "access_point": req.access_point,
            "message_id": req.message_id,
            "resident_id": str(req.resident_id) if req.resident_id else None,
            "device_host": req.device_host,
            "door_id": req.door_id,
            "method": req.method,
        },
        created_at=now,
    )
    session.add(audit)
    await session.flush()

    await session.commit()

    return LogOpenResponse(logged=True, audit_id=audit.id, access_log_id=access_log.id)
