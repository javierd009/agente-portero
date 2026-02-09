"""Intercom/FreePBX integration endpoints.

These endpoints are intended for internal telephony services (FreePBX bot/ext 1010).
They allow the PBX to:
- Create an authorization request for an intercom call (extension 1004/1005)
- Log DTMF actions (e.g. '*')

Security: currently relies on network boundary; add signed service token later.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from infrastructure.database import get_session
from domain.models.telephony_extension import TelephonyExtension
from domain.models.audit_log import AuditLog
from infrastructure.hikvision.client import HikvisionGateClient
from config import settings as app_settings

router = APIRouter()


def get_tenant_id(x_tenant_id: UUID = Header(..., description="Tenant/Condominium ID")) -> UUID:
    return x_tenant_id


class CallStartRequest(BaseModel):
    extension_called: str = Field(..., description="The intercom/PBX extension that was called (e.g., 1004, 1005)")
    bot_extension: Optional[str] = Field(default=None, description="Bot extension handling the call (e.g., 1010)")
    caller_id: Optional[str] = None
    target_unit: Optional[str] = None


class CallStartResponse(BaseModel):
    ok: bool
    access_point: str
    device_type: str
    door_id: int


@router.post("/call-start", response_model=CallStartResponse)
async def call_start(
    req: CallStartRequest,
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    q = (
        select(TelephonyExtension)
        .where(
            TelephonyExtension.condominium_id == tenant_id,
            TelephonyExtension.extension == req.extension_called,
            TelephonyExtension.enabled == True,
        )
        .limit(1)
    )
    row = (await session.execute(q)).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Unknown extension")

    # audit
    now = datetime.utcnow()
    session.add(
        AuditLog(
            condominium_id=tenant_id,
            actor_type="pbx",
            actor_id=req.bot_extension,
            actor_label="FreePBX",
            action="intercom_call_start",
            resource_type="extension",
            resource_id=None,
            status="success",
            message=f"call-start ext={req.extension_called}",
            extra_data={
                "extension_called": req.extension_called,
                "bot_extension": req.bot_extension,
                "caller_id": req.caller_id,
                "target_unit": req.target_unit,
                "access_point": row.access_point,
            },
            created_at=now,
        )
    )
    await session.commit()

    return CallStartResponse(ok=True, access_point=row.access_point, device_type=row.device_type, door_id=row.door_id)


class DtmfRequest(BaseModel):
    extension_called: str
    bot_extension: Optional[str] = None
    dtmf: str = Field(..., description="DTMF digit (e.g. '*')")
    caller_id: Optional[str] = None

    # If PBX already opened via phone function, set opened=true so we only log.
    opened: bool = False


class DtmfResponse(BaseModel):
    ok: bool
    opened: bool
    access_point: Optional[str] = None


@router.post("/dtmf", response_model=DtmfResponse)
async def dtmf(
    req: DtmfRequest,
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    now = datetime.utcnow()

    # Only handle '*' for now
    if req.dtmf != "*":
        session.add(
            AuditLog(
                condominium_id=tenant_id,
                actor_type="pbx",
                actor_id=req.bot_extension,
                actor_label="FreePBX",
                action="intercom_dtmf",
                resource_type="extension",
                resource_id=None,
                status="success",
                message=f"dtmf {req.dtmf}",
                extra_data={
                    "extension_called": req.extension_called,
                    "bot_extension": req.bot_extension,
                    "caller_id": req.caller_id,
                    "dtmf": req.dtmf,
                    "opened": False,
                },
                created_at=now,
            )
        )
        await session.commit()
        return DtmfResponse(ok=True, opened=False)

    # Lookup mapping
    q = (
        select(TelephonyExtension)
        .where(
            TelephonyExtension.condominium_id == tenant_id,
            TelephonyExtension.extension == req.extension_called,
            TelephonyExtension.enabled == True,
        )
        .limit(1)
    )
    row = (await session.execute(q)).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Unknown extension")

    opened = bool(req.opened)

    # If PBX didn't open, try to open via ISAPI for determinism + logs.
    if not opened:
        password = None
        if row.device_type == "panel":
            # Default panel credentials (keep secrets in env; host comes from mapping)
            password = getattr(app_settings, "hik_panel_password", None) or "integratec20"
        else:
            # biometrics
            if row.device_host == app_settings.hik_bio1_host:
                password = app_settings.hik_bio1_password
            elif row.device_host == app_settings.hik_bio2_host:
                password = app_settings.hik_bio2_password

        client = HikvisionGateClient(host=row.device_host, username=app_settings.hik_user, password=password or "")
        r = await client.open_gate(door_id=row.door_id)
        opened = bool(r.get("success"))

    session.add(
        AuditLog(
            condominium_id=tenant_id,
            actor_type="pbx",
            actor_id=req.bot_extension,
            actor_label="FreePBX",
            action="open_gate",
            resource_type="access_point",
            resource_id=None,
            status="success" if opened else "failure",
            message=f"dtmf * -> open {row.access_point}",
            extra_data={
                "extension_called": req.extension_called,
                "bot_extension": req.bot_extension,
                "caller_id": req.caller_id,
                "dtmf": "*",
                "opened": opened,
                "access_point": row.access_point,
                "device_type": row.device_type,
                "device_host": row.device_host,
                "door_id": row.door_id,
            },
            created_at=now,
        )
    )
    await session.commit()

    return DtmfResponse(ok=True, opened=opened, access_point=row.access_point)
