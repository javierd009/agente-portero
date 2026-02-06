"""Condominiums API - Tenant management"""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select

from infrastructure.database import get_session
from domain.models import Condominium
from domain.models.condominium import CondominiumCreate, CondominiumRead, CondominiumUpdate

router = APIRouter()


@router.get("/", response_model=List[CondominiumRead])
async def list_condominiums(
    session: AsyncSession = Depends(get_session),
    skip: int = 0,
    limit: int = 100,
    is_active: Optional[bool] = True,
):
    """List all condominiums (admin only in production)"""
    query = select(Condominium)

    if is_active is not None:
        query = query.where(Condominium.is_active == is_active)

    query = query.offset(skip).limit(limit)
    result = await session.execute(query)
    return result.scalars().all()


@router.post("/", response_model=CondominiumRead, status_code=201)
async def create_condominium(
    condominium: CondominiumCreate,
    session: AsyncSession = Depends(get_session),
):
    """Create a new condominium (admin only)"""
    # Check if slug is unique
    existing = await session.execute(
        select(Condominium).where(Condominium.slug == condominium.slug)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Slug already exists")

    db_condo = Condominium.model_validate(condominium)
    session.add(db_condo)
    await session.commit()
    await session.refresh(db_condo)
    return db_condo


@router.get("/{condominium_id}", response_model=CondominiumRead)
async def get_condominium(
    condominium_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """Get a specific condominium by ID"""
    query = select(Condominium).where(Condominium.id == condominium_id)
    result = await session.execute(query)
    condo = result.scalar_one_or_none()
    if not condo:
        raise HTTPException(status_code=404, detail="Condominium not found")
    return condo


@router.get("/slug/{slug}", response_model=CondominiumRead)
async def get_condominium_by_slug(
    slug: str,
    session: AsyncSession = Depends(get_session),
):
    """Get a condominium by slug"""
    query = select(Condominium).where(Condominium.slug == slug)
    result = await session.execute(query)
    condo = result.scalar_one_or_none()
    if not condo:
        raise HTTPException(status_code=404, detail="Condominium not found")
    return condo


@router.patch("/{condominium_id}", response_model=CondominiumRead)
async def update_condominium(
    condominium_id: UUID,
    condo_update: CondominiumUpdate,
    session: AsyncSession = Depends(get_session),
):
    """Update a condominium"""
    query = select(Condominium).where(Condominium.id == condominium_id)
    result = await session.execute(query)
    db_condo = result.scalar_one_or_none()
    if not db_condo:
        raise HTTPException(status_code=404, detail="Condominium not found")

    update_data = condo_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_condo, key, value)

    session.add(db_condo)
    await session.commit()
    await session.refresh(db_condo)
    return db_condo


@router.delete("/{condominium_id}", status_code=204)
async def delete_condominium(
    condominium_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """Delete a condominium (soft delete - sets is_active=False)"""
    query = select(Condominium).where(Condominium.id == condominium_id)
    result = await session.execute(query)
    condo = result.scalar_one_or_none()
    if not condo:
        raise HTTPException(status_code=404, detail="Condominium not found")

    condo.is_active = False
    session.add(condo)
    await session.commit()
