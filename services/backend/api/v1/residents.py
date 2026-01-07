"""Residents API - Resident management"""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select

from infrastructure.database import get_session
from domain.models import Resident
from domain.models.resident import ResidentCreate, ResidentRead, ResidentUpdate

router = APIRouter()


def get_tenant_id(x_tenant_id: UUID = Header(..., description="Tenant/Condominium ID")) -> UUID:
    """Extract tenant ID from header for multi-tenant isolation"""
    return x_tenant_id


@router.get("/", response_model=List[ResidentRead])
async def list_residents(
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
    skip: int = 0,
    limit: int = 100,
    unit: Optional[str] = None,
):
    """List all residents for a condominium"""
    query = select(Resident).where(Resident.condominium_id == tenant_id)

    if unit:
        query = query.where(Resident.unit == unit)

    query = query.offset(skip).limit(limit)
    result = await session.execute(query)
    return result.scalars().all()


@router.get("/by-phone/{phone}", response_model=ResidentRead)
async def get_resident_by_phone(
    phone: str,
    session: AsyncSession = Depends(get_session),
):
    """
    Get resident by phone number (for WhatsApp service)
    Note: No tenant_id required - phone is globally unique
    """
    query = select(Resident).where(Resident.whatsapp == phone)
    result = await session.execute(query)
    resident = result.scalar_one_or_none()

    if not resident:
        raise HTTPException(status_code=404, detail="Resident not found")

    return resident


@router.post("/", response_model=ResidentRead, status_code=201)
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


@router.get("/{resident_id}", response_model=ResidentRead)
async def get_resident(
    resident_id: UUID,
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """Get a specific resident by ID"""
    query = select(Resident).where(
        Resident.id == resident_id,
        Resident.condominium_id == tenant_id
    )
    result = await session.execute(query)
    resident = result.scalar_one_or_none()

    if not resident:
        raise HTTPException(status_code=404, detail="Resident not found")

    return resident


@router.patch("/{resident_id}", response_model=ResidentRead)
async def update_resident(
    resident_id: UUID,
    resident_update: ResidentUpdate,
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """Update a resident"""
    query = select(Resident).where(
        Resident.id == resident_id,
        Resident.condominium_id == tenant_id
    )
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


@router.delete("/{resident_id}", status_code=204)
async def delete_resident(
    resident_id: UUID,
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """Delete a resident"""
    query = select(Resident).where(
        Resident.id == resident_id,
        Resident.condominium_id == tenant_id
    )
    result = await session.execute(query)
    resident = result.scalar_one_or_none()

    if not resident:
        raise HTTPException(status_code=404, detail="Resident not found")

    await session.delete(resident)
    await session.commit()
    return None
