"""Vehicle model"""
from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field
from uuid import UUID, uuid4

class VehicleBase(SQLModel):
    condominium_id: UUID = Field(foreign_key="condominiums.id", index=True)
    resident_id: UUID = Field(foreign_key="residents.id", index=True)
    plate: str = Field(index=True)  # License plate
    brand: Optional[str] = None
    model: Optional[str] = None
    color: Optional[str] = None
    is_active: bool = Field(default=True)

class Vehicle(VehicleBase, table=True):
    __tablename__ = "vehicles"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class VehicleCreate(VehicleBase):
    pass

class VehicleRead(VehicleBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

class VehicleUpdate(SQLModel):
    plate: Optional[str] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    color: Optional[str] = None
    is_active: Optional[bool] = None
