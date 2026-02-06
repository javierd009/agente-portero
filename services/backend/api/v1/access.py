"""Access API - Access logs and visitor management"""
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Header, Query
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select, and_

from infrastructure.database import get_session
from domain.models import AccessLog, Resident, Visitor
from domain.models.access_log import AccessLogCreate, AccessLogRead
from domain.models.resident import ResidentCreate, ResidentRead, ResidentUpdate
from domain.models.visitor import VisitorCreate, VisitorRead

router = APIRouter()


def get_tenant_id(x_tenant_id: UUID = Header(..., description="Tenant/Condominium ID")) -> UUID:
    return x_tenant_id


# === Access Logs ===

@router.get("/logs", response_model=List[AccessLogRead])
async def list_access_logs(
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
    skip: int = 0,
    limit: int = 100,
    access_type: Optional[str] = Query(None, description="Filter by type: entry, exit, denied"),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    resident_id: Optional[UUID] = Query(None, description="Filter by resident"),
    visitor_name: Optional[str] = Query(None, description="Search visitor by name"),
    query_type: Optional[str] = Query(None, description="Quick filter: today, yesterday, week"),
):
    """List access logs for a condominium with optional filters"""
    query = select(AccessLog).where(AccessLog.condominium_id == tenant_id)

    if access_type:
        query = query.where(AccessLog.event_type == access_type)

    if resident_id:
        query = query.where(AccessLog.resident_id == resident_id)

    if visitor_name:
        query = query.where(AccessLog.visitor_name.ilike(f"%{visitor_name}%"))

    # Quick date filters (for WhatsApp service)
    if query_type:
        from datetime import timedelta
        now = datetime.utcnow()

        if query_type == "today":
            start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
            query = query.where(AccessLog.created_at >= start_of_day)
        elif query_type == "yesterday":
            start_of_yesterday = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_yesterday = now.replace(hour=0, minute=0, second=0, microsecond=0)
            query = query.where(
                and_(
                    AccessLog.created_at >= start_of_yesterday,
                    AccessLog.created_at < end_of_yesterday
                )
            )
        elif query_type == "week":
            start_of_week = now - timedelta(days=7)
            query = query.where(AccessLog.created_at >= start_of_week)

    if start_date:
        query = query.where(AccessLog.created_at >= start_date)
    if end_date:
        query = query.where(AccessLog.created_at <= end_date)

    query = query.order_by(AccessLog.created_at.desc()).offset(skip).limit(limit)
    result = await session.execute(query)
    return result.scalars().all()


@router.post("/logs", response_model=AccessLogRead, status_code=201)
async def create_access_log(
    log: AccessLogCreate,
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """Create a new access log entry"""
    if log.condominium_id != tenant_id:
        raise HTTPException(status_code=403, detail="Cannot create log for different tenant")

    db_log = AccessLog.model_validate(log)
    session.add(db_log)
    await session.commit()
    await session.refresh(db_log)
    return db_log


# === Residents ===

@router.get("/residents", response_model=List[ResidentRead])
async def list_residents(
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
    skip: int = 0,
    limit: int = 100,
    unit: Optional[str] = Query(None, description="Filter by unit number"),
):
    """List all residents for a condominium"""
    query = select(Resident).where(Resident.condominium_id == tenant_id)

    if unit:
        query = query.where(Resident.unit == unit)

    query = query.offset(skip).limit(limit)
    result = await session.execute(query)
    return result.scalars().all()


@router.post("/residents", response_model=ResidentRead, status_code=201)
async def create_resident(
    resident: ResidentCreate,
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """Create a new resident"""
    if resident.condominium_id != tenant_id:
        raise HTTPException(status_code=403, detail="Cannot create resident for different tenant")

    db_resident = Resident.model_validate(resident)
    session.add(db_resident)
    await session.commit()
    await session.refresh(db_resident)
    return db_resident


@router.get("/residents/{resident_id}", response_model=ResidentRead)
async def get_resident(
    resident_id: UUID,
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """Get a specific resident"""
    query = select(Resident).where(Resident.id == resident_id, Resident.condominium_id == tenant_id)
    result = await session.execute(query)
    resident = result.scalar_one_or_none()
    if not resident:
        raise HTTPException(status_code=404, detail="Resident not found")
    return resident


@router.patch("/residents/{resident_id}", response_model=ResidentRead)
async def update_resident(
    resident_id: UUID,
    resident_update: ResidentUpdate,
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """Update a resident"""
    query = select(Resident).where(Resident.id == resident_id, Resident.condominium_id == tenant_id)
    result = await session.execute(query)
    db_resident = result.scalar_one_or_none()
    if not db_resident:
        raise HTTPException(status_code=404, detail="Resident not found")

    update_data = resident_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_resident, key, value)

    session.add(db_resident)
    await session.commit()
    await session.refresh(db_resident)
    return db_resident


# === Visitors ===

@router.get("/visitors", response_model=List[VisitorRead])
async def list_visitors(
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
    skip: int = 0,
    limit: int = 100,
    is_authorized: Optional[bool] = None,
):
    """List visitors for a condominium"""
    query = select(Visitor).where(Visitor.condominium_id == tenant_id)

    if is_authorized is not None:
        status = "approved" if is_authorized else "denied"
        query = query.where(Visitor.status == status)

    query = query.order_by(Visitor.created_at.desc()).offset(skip).limit(limit)
    result = await session.execute(query)
    return result.scalars().all()


@router.post("/visitors", response_model=VisitorRead, status_code=201)
async def create_visitor(
    visitor: VisitorCreate,
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """Register a new visitor"""
    if visitor.condominium_id != tenant_id:
        raise HTTPException(status_code=403, detail="Cannot create visitor for different tenant")

    db_visitor = Visitor.model_validate(visitor)
    session.add(db_visitor)
    await session.commit()
    await session.refresh(db_visitor)
    return db_visitor


@router.get("/visitors/check")
async def check_visitor_authorization(
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
    name: Optional[str] = Query(None),
    plate: Optional[str] = Query(None),
    id_number: Optional[str] = Query(None),
):
    """Check if a visitor is authorized (for voice agent use)"""
    if not any([name, plate, id_number]):
        raise HTTPException(status_code=400, detail="Must provide name, plate, or id_number")

    query = select(Visitor).where(
        Visitor.condominium_id == tenant_id,
        Visitor.status == "approved"
    )

    conditions = []
    if name:
        conditions.append(Visitor.name.ilike(f"%{name}%"))
    if plate:
        conditions.append(Visitor.vehicle_plate == plate)
    if id_number:
        conditions.append(Visitor.id_number == id_number)

    if conditions:
        from sqlalchemy import or_
        query = query.where(or_(*conditions))

    result = await session.execute(query)
    visitor = result.scalar_one_or_none()

    return {
        "authorized": visitor is not None,
        "visitor": VisitorRead.model_validate(visitor) if visitor else None
    }
