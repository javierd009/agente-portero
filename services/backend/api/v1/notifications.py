"""Notifications API - WhatsApp and push notifications"""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Header, BackgroundTasks
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select

from infrastructure.database import get_session
from domain.models import Notification, Resident
from domain.models.notification import NotificationCreate, NotificationRead

router = APIRouter()


def get_tenant_id(x_tenant_id: UUID = Header(..., description="Tenant/Condominium ID")) -> UUID:
    return x_tenant_id


@router.get("/", response_model=List[NotificationRead])
async def list_notifications(
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
):
    """List notifications for a condominium"""
    query = select(Notification).where(Notification.condominium_id == tenant_id)

    if status:
        query = query.where(Notification.status == status)

    query = query.order_by(Notification.created_at.desc()).offset(skip).limit(limit)
    result = await session.execute(query)
    return result.scalars().all()


@router.post("/", response_model=NotificationRead, status_code=201)
async def create_notification(
    notification: NotificationCreate,
    background_tasks: BackgroundTasks,
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """Create and send a notification"""
    if notification.condominium_id != tenant_id:
        raise HTTPException(status_code=403, detail="Cannot create notification for different tenant")

    db_notification = Notification.model_validate(notification)
    session.add(db_notification)
    await session.commit()
    await session.refresh(db_notification)

    # Queue notification delivery in background
    background_tasks.add_task(send_notification_async, db_notification.id, notification.channel)

    return db_notification


@router.post("/visitor-arrival")
async def notify_visitor_arrival(
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
    background_tasks: BackgroundTasks = None,
    resident_id: UUID = None,
    visitor_name: str = None,
    visitor_plate: Optional[str] = None,
    snapshot_url: Optional[str] = None,
):
    """Notify resident of visitor arrival (convenience endpoint for voice agent)"""
    # Get resident info
    query = select(Resident).where(
        Resident.id == resident_id,
        Resident.condominium_id == tenant_id
    )
    result = await session.execute(query)
    resident = result.scalar_one_or_none()

    if not resident:
        raise HTTPException(status_code=404, detail="Resident not found")

    if not resident.whatsapp:
        return {"sent": False, "reason": "Resident has no WhatsApp configured"}

    # Create notification record
    message = f"Visitante en puerta: {visitor_name}"
    if visitor_plate:
        message += f" (Placa: {visitor_plate})"

    notification = Notification(
        condominium_id=tenant_id,
        resident_id=resident_id,
        channel="whatsapp",
        recipient=resident.whatsapp,
        notification_type="visitor_arrived",
        title="Visitante en puerta",
        message=message,
        metadata={"visitor_name": visitor_name, "plate": visitor_plate, "snapshot": snapshot_url}
    )
    session.add(notification)
    await session.commit()
    await session.refresh(notification)

    # Queue delivery
    if background_tasks:
        background_tasks.add_task(send_whatsapp_notification, resident.whatsapp, message, snapshot_url)

    return {"sent": True, "notification_id": notification.id}


async def send_notification_async(notification_id: UUID, channel: str):
    """Background task to send notification via appropriate channel"""
    from infrastructure.whatsapp import EvolutionAPIClient
    from infrastructure.database import async_session_maker

    async with async_session_maker() as session:
        query = select(Notification).where(Notification.id == notification_id)
        result = await session.execute(query)
        notification = result.scalar_one_or_none()

        if not notification:
            return

        try:
            if channel == "whatsapp":
                client = EvolutionAPIClient()
                wa_result = await client.send_text_message(
                    notification.recipient,
                    notification.message
                )

                if "error" not in wa_result:
                    notification.status = "sent"
                else:
                    notification.status = "failed"
                    notification.error_message = str(wa_result.get("error"))
            else:
                # Other channels not implemented yet
                notification.status = "pending"

            session.add(notification)
            await session.commit()

        except Exception as e:
            notification.status = "failed"
            notification.error_message = str(e)
            session.add(notification)
            await session.commit()


async def send_whatsapp_notification(phone: str, message: str, image_url: Optional[str] = None):
    """Send WhatsApp message via Evolution API"""
    from infrastructure.whatsapp import EvolutionAPIClient

    client = EvolutionAPIClient()

    if image_url:
        await client.send_media_message(phone, image_url, caption=message)
    else:
        await client.send_text_message(phone, message)
