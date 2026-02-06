"""QR Operations API - revoke and consume.

MVP mode (no auth): requires resident_id in body for revoke and uses tenant header.
Future mode: resident_id will be inferred from Supabase JWT.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from infrastructure.database import get_session
from domain.models.qr_token import QrToken
from domain.models.access_credential import AccessCredential
from domain.models.audit_log import AuditLog
from domain.models.access_log import AccessLog
from infrastructure.hikvision.client import HikvisionGateClient
from config import settings as app_settings

router = APIRouter()

AccessPoint = Literal["vehicular_entry", "vehicular_exit", "pedestrian"]
Direction = Literal["entry", "exit"]


def get_tenant_id(x_tenant_id: UUID = Header(..., description="Tenant/Condominium ID")) -> UUID:
    return x_tenant_id


def _to_naive_utc(dt: datetime) -> datetime:
    """Normalize datetime for DB columns defined as TIMESTAMP WITHOUT TIME ZONE."""
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


class RevokeQrRequest(BaseModel):
    resident_id: UUID
    token: str
    reason: Optional[str] = None


class RevokeQrResponse(BaseModel):
    revoked: bool
    token: str


class ConsumeQrRequest(BaseModel):
    token: str
    access_point: AccessPoint
    direction: Direction = "entry"  # default for most condos


class ConsumeQrResponse(BaseModel):
    accepted: bool
    token: str
    direction: Direction
    access_point: AccessPoint
    use_count: int
    max_uses: Optional[int] = None

    gate_opened: bool
    gate_method: Optional[str] = None


@router.post("/revoke", response_model=RevokeQrResponse)
async def revoke_qr(
    req: RevokeQrRequest,
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    res = await session.execute(select(QrToken).where(QrToken.token == req.token))
    qr = res.scalar_one_or_none()
    if not qr or qr.condominium_id != tenant_id:
        raise HTTPException(status_code=404, detail="QR not found")

    # Ownership check (MVP)
    if qr.resident_id != req.resident_id:
        raise HTTPException(status_code=403, detail="Cannot revoke QR not issued by you")

    now = datetime.utcnow()
    if not qr.revoked_at:
        qr.revoked_at = now

    # Revoke credential if present
    if qr.credential_id:
        cres = await session.execute(select(AccessCredential).where(AccessCredential.id == qr.credential_id))
        cred = cres.scalar_one_or_none()
        if cred and cred.condominium_id == tenant_id:
            cred.status = "revoked"
            cred.revoked_at = now

    audit = AuditLog(
        condominium_id=tenant_id,
        actor_type="resident",
        actor_id=str(req.resident_id),
        actor_label=None,
        action="revoke_qr",
        resource_type="qr_token",
        resource_id=qr.id,
        status="success",
        message=req.reason or "QR revoked",
        extra_data={"token": req.token},
    )
    session.add(audit)

    await session.commit()
    return RevokeQrResponse(revoked=True, token=req.token)


@router.post("/consume", response_model=ConsumeQrResponse)
async def consume_qr(
    req: ConsumeQrRequest,
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    res = await session.execute(select(QrToken).where(QrToken.token == req.token))
    qr = res.scalar_one_or_none()
    if not qr or qr.condominium_id != tenant_id:
        raise HTTPException(status_code=404, detail="QR not found")

    now = _to_naive_utc(datetime.now(timezone.utc))

    if qr.revoked_at:
        raise HTTPException(status_code=410, detail="QR revoked")

    expires_at = _to_naive_utc(qr.expires_at)
    if expires_at <= now:
        raise HTTPException(status_code=410, detail="QR expired")

    allowed = set(qr.allowed_access_points or [])
    if req.access_point not in allowed:
        raise HTTPException(status_code=403, detail="Access point not allowed")

    if qr.max_uses is not None and qr.use_count >= qr.max_uses:
        raise HTTPException(status_code=410, detail="QR usage limit reached")

    # Update counters
    qr.use_count += 1
    qr.used_at = now

    # Mirror in credential
    cred: Optional[AccessCredential] = None
    if qr.credential_id:
        cres = await session.execute(select(AccessCredential).where(AccessCredential.id == qr.credential_id))
        cred = cres.scalar_one_or_none()
        if cred and cred.condominium_id == tenant_id:
            cred.use_count = (cred.use_count or 0) + 1
            cred.used_at = now
            # enforce credential max_uses if set
            if cred.max_uses is not None and cred.use_count >= cred.max_uses:
                cred.status = "used"

    # Open gate immediately (Sitnova mapping via env/config)
    door_id = 1
    host = app_settings.hik_panel_host
    port = app_settings.hik_panel_port
    password = app_settings.hik_pass_default

    if req.access_point == "vehicular_entry":
        door_id = 1
        host = app_settings.hik_panel_host
        port = app_settings.hik_panel_port
        password = app_settings.hik_pass_default
    elif req.access_point == "vehicular_exit":
        door_id = 2
        host = app_settings.hik_panel_host
        port = app_settings.hik_panel_port
        password = app_settings.hik_pass_default
    elif req.access_point == "pedestrian":
        door_id = 1
        host = app_settings.hik_pedestrian_host
        port = app_settings.hik_pedestrian_port
        password = app_settings.hik_pass_pedestrian

    # Ensure timeout matches config
    import os
    os.environ["HIKVISION_TIMEOUT"] = str(app_settings.hik_timeout_seconds)

    gate_client = HikvisionGateClient(host=host, port=port, username=app_settings.hik_user, password=password)
    gate_result = await gate_client.open_gate(door_id=door_id)
    gate_opened = bool(gate_result.get("success"))
    gate_method = gate_result.get("method") if gate_opened else None

    # Access log
    access_log = AccessLog(
        condominium_id=tenant_id,
        event_type=req.direction,
        access_point=req.access_point,
        direction=req.direction,
        resident_id=qr.resident_id,
        visitor_id=qr.visitor_id,
        visitor_name=(qr.extra_data or {}).get("visitor_name"),
        vehicle_plate=None,
        authorization_method="qr",
        authorized_by=str(qr.resident_id) if qr.resident_id else None,
        camera_snapshot_url=None,
        confidence_score=None,
        extra_data={
            "token_id": str(qr.id),
            "gate_opened": gate_opened,
            "gate_method": gate_method,
            "device_host": host,
            "door_id": door_id,
        },
    )
    session.add(access_log)

    audit = AuditLog(
        condominium_id=tenant_id,
        actor_type="system",
        actor_id=None,
        actor_label="qr_consume",
        action="consume_qr",
        resource_type="qr_token",
        resource_id=qr.id,
        status="success" if gate_opened else "failure",
        message=f"consumed at {req.access_point} ({req.direction}); opened={gate_opened}",
        extra_data={
            "access_point": req.access_point,
            "direction": req.direction,
            "gate_opened": gate_opened,
            "gate_method": gate_method,
        },
    )
    session.add(audit)

    await session.commit()

    return ConsumeQrResponse(
        accepted=True,
        token=req.token,
        direction=req.direction,
        access_point=req.access_point,
        use_count=qr.use_count,
        max_uses=qr.max_uses,
        gate_opened=gate_opened,
        gate_method=gate_method,
    )
