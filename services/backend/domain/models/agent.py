"""Agent (AI Virtual Guard) model"""
from typing import Optional, Dict, Any
from datetime import datetime
from sqlmodel import SQLModel, Field, Column
from sqlalchemy import JSON
from uuid import UUID, uuid4


class AgentBase(SQLModel):
    condominium_id: UUID = Field(foreign_key="condominiums.id", index=True)
    name: str = Field(default="Agente Virtual")
    extension: str = Field(index=True)  # SIP extension (e.g., "100")
    prompt: str = Field(default="")  # System prompt for AI
    voice_id: Optional[str] = None  # OpenAI voice ID
    language: str = Field(default="es-MX")
    is_active: bool = Field(default=True)
    settings: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))

class Agent(AgentBase, table=True):
    __tablename__ = "agents"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class AgentCreate(AgentBase):
    pass

class AgentRead(AgentBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

class AgentUpdate(SQLModel):
    name: Optional[str] = None
    extension: Optional[str] = None
    prompt: Optional[str] = None
    voice_id: Optional[str] = None
    language: Optional[str] = None
    is_active: Optional[bool] = None
    settings: Optional[Dict[str, Any]] = None
