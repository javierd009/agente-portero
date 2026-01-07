"""Condominium (Tenant) model"""
from typing import Optional, Dict, Any
from datetime import datetime
from sqlmodel import SQLModel, Field, Column
from sqlalchemy import JSON
from uuid import UUID, uuid4


class CondominiumBase(SQLModel):
    name: str = Field(index=True)
    slug: str = Field(unique=True, index=True)
    address: Optional[str] = None
    timezone: str = Field(default="America/Mexico_City")
    settings: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    is_active: bool = Field(default=True)

class Condominium(CondominiumBase, table=True):
    __tablename__ = "condominiums"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class CondominiumCreate(CondominiumBase):
    pass

class CondominiumRead(CondominiumBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

class CondominiumUpdate(SQLModel):
    name: Optional[str] = None
    address: Optional[str] = None
    timezone: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
