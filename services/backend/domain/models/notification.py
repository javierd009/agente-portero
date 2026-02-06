"""Notification model - WhatsApp/SMS/Voice notifications"""
from typing import Optional, Dict, Any
from datetime import datetime
from sqlmodel import SQLModel, Field, Column
from sqlalchemy import JSON
from uuid import UUID, uuid4


class NotificationBase(SQLModel):
    condominium_id: UUID = Field(foreign_key="condominiums.id", index=True)
    resident_id: Optional[UUID] = Field(foreign_key="residents.id", default=None)

    channel: str  # 'whatsapp', 'sms', 'voice', 'push'
    recipient: str  # Phone number or push token

    notification_type: str  # 'visitor_arrived', 'access_granted', 'alert', 'system'
    title: str
    message: str

    # Status
    status: str = Field(default="pending")  # pending, sent, delivered, failed
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    error_message: Optional[str] = None

    # Reference
    related_visitor_id: Optional[UUID] = Field(foreign_key="visitors.id", default=None)
    related_access_log_id: Optional[UUID] = Field(foreign_key="access_logs.id", default=None)

    extra_data: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))


class Notification(NotificationBase, table=True):
    __tablename__ = "notifications"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class NotificationCreate(NotificationBase):
    pass

class NotificationRead(NotificationBase):
    id: UUID
    created_at: datetime
