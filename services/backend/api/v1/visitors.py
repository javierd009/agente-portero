"""Visitors API - Visitor authorization and management"""
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from pydantic import BaseModel

from infrastructure.database import get_session
from domain.models import Visitor
from domain.models.visitor import VisitorCreate, VisitorRead, VisitorUpdate

router = APIRouter()


def get_tenant_id(x_tenant_id: UUID = Header(..., description="Tenant/Condominium ID")) -> UUID:
    """Extract tenant ID from header for multi-tenant isolation"""
    return x_tenant_id


class VisitorAuthorizeRequest(BaseModel):
    """Request to authorize a visitor (from WhatsApp service)"""
    condominium_id: UUID
    resident_id: UUID
    visitor_name: str
    vehicle_plate: Optional[str] = None
    valid_until: Optional[datetime] = None
    notes: Optional[str] = None


@router.post("/authorize", response_model=VisitorRead, status_code=201)
async def authorize_visitor(
    request: VisitorAuthorizeRequest,
    session: AsyncSession = Depends(get_session),
):
    """
    Authorize a visitor (temporary pre-authorization)
    Called by WhatsApp service when resident authorizes someone
    """
    # Calculate valid_until if not provided (default 2 hours)
    if not request.valid_until:
        request.valid_until = datetime.utcnow() + timedelta(hours=2)

    # Create visitor with approved status
    visitor = Visitor(
        condominium_id=request.condominium_id,
        resident_id=request.resident_id,
        name=request.visitor_name,
        vehicle_plate=request.vehicle_plate,
        valid_until=request.valid_until,
        notes=request.notes or "Authorized via WhatsApp",
        authorized_by="whatsapp",
        status="approved"
    )

    session.add(visitor)
    await session.commit()
    await session.refresh(visitor)
    return visitor


@router.get("/check-authorization/{visitor_name}", response_model=Optional[VisitorRead])
async def check_visitor_authorization(
    visitor_name: str,
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
    resident_id: Optional[UUID] = None,
):
    """
    Check if a visitor is authorized
    Used by Voice service during call
    """
    query = select(Visitor).where(
        Visitor.condominium_id == tenant_id,
        Visitor.name.ilike(f"%{visitor_name}%"),
        Visitor.status == "approved",
        Visitor.valid_until > datetime.utcnow()
    )

    if resident_id:
        query = query.where(Visitor.resident_id == resident_id)

    result = await session.execute(query)
    visitor = result.scalar_one_or_none()

    return visitor


@router.get("/", response_model=List[VisitorRead])
async def list_visitors(
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    resident_id: Optional[UUID] = None,
):
    """List all visitors for a condominium"""
    query = select(Visitor).where(Visitor.condominium_id == tenant_id)

    if status:
        query = query.where(Visitor.status == status)

    if resident_id:
        query = query.where(Visitor.resident_id == resident_id)

    query = query.offset(skip).limit(limit).order_by(Visitor.created_at.desc())
    result = await session.execute(query)
    return result.scalars().all()


@router.post("/", response_model=VisitorRead, status_code=201)
async def create_visitor(
    visitor: VisitorCreate,
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """Create a new visitor"""
    if visitor.condominium_id != tenant_id:
        raise HTTPException(status_code=403, detail="Cannot create visitor for different tenant")

    db_visitor = Visitor.model_validate(visitor)
    session.add(db_visitor)
    await session.commit()
    await session.refresh(db_visitor)
    return db_visitor


@router.get("/{visitor_id}", response_model=VisitorRead)
async def get_visitor(
    visitor_id: UUID,
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """Get a specific visitor by ID"""
    query = select(Visitor).where(
        Visitor.id == visitor_id,
        Visitor.condominium_id == tenant_id
    )
    result = await session.execute(query)
    visitor = result.scalar_one_or_none()

    if not visitor:
        raise HTTPException(status_code=404, detail="Visitor not found")

    return visitor


@router.patch("/{visitor_id}", response_model=VisitorRead)
async def update_visitor(
    visitor_id: UUID,
    visitor_update: VisitorUpdate,
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """Update a visitor"""
    query = select(Visitor).where(
        Visitor.id == visitor_id,
        Visitor.condominium_id == tenant_id
    )
    result = await session.execute(query)
    db_visitor = result.scalar_one_or_none()

    if not db_visitor:
        raise HTTPException(status_code=404, detail="Visitor not found")

    update_data = visitor_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_visitor, key, value)

    session.add(db_visitor)
    await session.commit()
    await session.refresh(db_visitor)
    return db_visitor


@router.delete("/{visitor_id}", status_code=204)
async def delete_visitor(
    visitor_id: UUID,
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """Delete a visitor"""
    query = select(Visitor).where(
        Visitor.id == visitor_id,
        Visitor.condominium_id == tenant_id
    )
    result = await session.execute(query)
    visitor = result.scalar_one_or_none()

    if not visitor:
        raise HTTPException(status_code=404, detail="Visitor not found")

    await session.delete(visitor)
    await session.commit()
    return None
