"""Agents API - Virtual guard agent management"""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select

from infrastructure.database import get_session
from domain.models import Agent
from domain.models.agent import AgentCreate, AgentRead, AgentUpdate

router = APIRouter()


def get_tenant_id(x_tenant_id: UUID = Header(..., description="Tenant/Condominium ID")) -> UUID:
    """Extract tenant ID from header for multi-tenant isolation"""
    return x_tenant_id


@router.get("/", response_model=List[AgentRead])
async def list_agents(
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
    skip: int = 0,
    limit: int = 100,
):
    """List all agents for a condominium"""
    query = select(Agent).where(Agent.condominium_id == tenant_id).offset(skip).limit(limit)
    result = await session.execute(query)
    return result.scalars().all()


@router.post("/", response_model=AgentRead, status_code=201)
async def create_agent(
    agent: AgentCreate,
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """Create a new virtual guard agent"""
    if agent.condominium_id != tenant_id:
        raise HTTPException(status_code=403, detail="Cannot create agent for different tenant")

    db_agent = Agent.model_validate(agent)
    session.add(db_agent)
    await session.commit()
    await session.refresh(db_agent)
    return db_agent


@router.get("/{agent_id}", response_model=AgentRead)
async def get_agent(
    agent_id: UUID,
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """Get a specific agent by ID"""
    query = select(Agent).where(Agent.id == agent_id, Agent.condominium_id == tenant_id)
    result = await session.execute(query)
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.patch("/{agent_id}", response_model=AgentRead)
async def update_agent(
    agent_id: UUID,
    agent_update: AgentUpdate,
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """Update an agent"""
    query = select(Agent).where(Agent.id == agent_id, Agent.condominium_id == tenant_id)
    result = await session.execute(query)
    db_agent = result.scalar_one_or_none()
    if not db_agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    update_data = agent_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_agent, key, value)

    session.add(db_agent)
    await session.commit()
    await session.refresh(db_agent)
    return db_agent


@router.delete("/{agent_id}", status_code=204)
async def delete_agent(
    agent_id: UUID,
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """Delete an agent"""
    query = select(Agent).where(Agent.id == agent_id, Agent.condominium_id == tenant_id)
    result = await session.execute(query)
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    await session.delete(agent)
    await session.commit()
