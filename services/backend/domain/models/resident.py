"""Resident model"""
from typing import Optional, List
from datetime import datetime
from sqlmodel import SQLModel, Field, Column
from sqlalchemy import JSON
from uuid import UUID, uuid4


class ResidentBase(SQLModel):
    condominium_id: UUID = Field(foreign_key="condominiums.id", index=True)
    user_id: Optional[UUID] = None  # Link to Supabase auth.users
    name: str = Field(index=True)
    unit: str = Field(index=True)  # "A-101", "B-205"
    phone: Optional[str] = None
    email: Optional[str] = None
    whatsapp: Optional[str] = None  # For Evolution API notifications
    authorized_visitors: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    is_active: bool = Field(default=True)

class Resident(ResidentBase, table=True):
    __tablename__ = "residents"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class ResidentCreate(ResidentBase):
    pass

class ResidentRead(ResidentBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

class ResidentUpdate(SQLModel):
    name: Optional[str] = None
    unit: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    whatsapp: Optional[str] = None
    authorized_visitors: Optional[List[str]] = None
    is_active: Optional[bool] = None
