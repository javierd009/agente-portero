"""Gates API - Access gate control"""
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Header, BackgroundTasks
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from pydantic import BaseModel

from infrastructure.database import get_session
from infrastructure.hikvision import HikvisionGateClient
from domain.models import Condominium, AccessLog

router = APIRouter()


class GateCommand(BaseModel):
    gate_id: str = "main_gate"
    door_number: int = 1
    visitor_name: Optional[str] = None
    resident_id: Optional[UUID] = None
    reason: Optional[str] = None


def get_tenant_id(x_tenant_id: UUID = Header(..., description="Tenant/Condominium ID")) -> UUID:
    return x_tenant_id


@router.post("/open")
async def open_gate(
    command: GateCommand,
    background_tasks: BackgroundTasks,
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """Open access gate"""
    # Get condominium settings
    query = select(Condominium).where(Condominium.id == tenant_id)
    result = await session.execute(query)
    condo = result.scalar_one_or_none()

    if not condo:
        raise HTTPException(status_code=404, detail="Condominium not found")

    # Get gate configuration from settings
    settings = condo.settings or {}
    gate_config = settings.get("gates", {}).get(command.gate_id, {})

    hikvision_host = gate_config.get("hikvision_host") or settings.get("hikvision_host")
    hikvision_user = gate_config.get("hikvision_user") or settings.get("hikvision_user")
    hikvision_password = gate_config.get("hikvision_password") or settings.get("hikvision_password")

    if not hikvision_host:
        raise HTTPException(status_code=400, detail="Gate not configured for this condominium")

    # Open the gate
    client = HikvisionGateClient(
        host=hikvision_host,
        username=hikvision_user,
        password=hikvision_password
    )

    result = await client.open_gate(door_id=command.door_number)

    if result.get("success"):
        # Log the access event in background
        background_tasks.add_task(
            log_gate_access,
            session,
            tenant_id,
            command,
            "gate_opened"
        )
        return {
            "success": True,
            "message": "Gate opened successfully",
            "method": result.get("method")
        }
    else:
        return {
            "success": False,
            "error": result.get("error", "Failed to open gate")
        }


@router.post("/close")
async def close_gate(
    command: GateCommand,
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """Close access gate (if supported by hardware)"""
    # Get condominium settings
    query = select(Condominium).where(Condominium.id == tenant_id)
    result = await session.execute(query)
    condo = result.scalar_one_or_none()

    if not condo:
        raise HTTPException(status_code=404, detail="Condominium not found")

    settings = condo.settings or {}
    gate_config = settings.get("gates", {}).get(command.gate_id, {})

    hikvision_host = gate_config.get("hikvision_host") or settings.get("hikvision_host")
    hikvision_user = gate_config.get("hikvision_user") or settings.get("hikvision_user")
    hikvision_password = gate_config.get("hikvision_password") or settings.get("hikvision_password")

    if not hikvision_host:
        raise HTTPException(status_code=400, detail="Gate not configured")

    client = HikvisionGateClient(
        host=hikvision_host,
        username=hikvision_user,
        password=hikvision_password
    )

    result = await client.close_gate(door_id=command.door_number)

    return {
        "success": result.get("success", False),
        "message": "Gate close command sent" if result.get("success") else "Failed"
    }


@router.get("/status/{gate_id}")
async def get_gate_status(
    gate_id: str,
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """Get gate status"""
    # Get condominium settings
    query = select(Condominium).where(Condominium.id == tenant_id)
    result = await session.execute(query)
    condo = result.scalar_one_or_none()

    if not condo:
        raise HTTPException(status_code=404, detail="Condominium not found")

    settings = condo.settings or {}
    gate_config = settings.get("gates", {}).get(gate_id, {})

    hikvision_host = gate_config.get("hikvision_host") or settings.get("hikvision_host")

    if not hikvision_host:
        return {"configured": False, "status": "not_configured"}

    client = HikvisionGateClient(
        host=hikvision_host,
        username=gate_config.get("hikvision_user") or settings.get("hikvision_user"),
        password=gate_config.get("hikvision_password") or settings.get("hikvision_password")
    )

    connected = await client.check_connection()

    return {
        "configured": True,
        "connected": connected,
        "gate_id": gate_id,
        "host": hikvision_host
    }


async def log_gate_access(
    session: AsyncSession,
    tenant_id: UUID,
    command: GateCommand,
    event_type: str
):
    """Log gate access event"""
    from infrastructure.database import async_session_maker

    async with async_session_maker() as new_session:
        log = AccessLog(
            condominium_id=tenant_id,
            event_type=event_type,
            access_point=command.gate_id,
            visitor_name=command.visitor_name,
            authorization_method="api_command",
            resident_id=command.resident_id,
            metadata={"reason": command.reason}
        )
        new_session.add(log)
        await new_session.commit()
