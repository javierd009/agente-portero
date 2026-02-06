"""QR API - Issue branded QR cards for visitor access.

Design goals:
- Scalable: generic access_credentials + qr_tokens
- Tenant isolation: x-tenant-id header
- Audit everything: audit_logs
- Branding-ready: render a card image (PNG) with condo name + Sitnova branding

NOTE: Auth/RBAC will be enforced at the gateway layer (WhatsApp service / dashboard)
and later via Supabase JWT. For now, we still enforce tenant_id boundaries.
"""

from __future__ import annotations

import base64
import io
import secrets
from datetime import datetime
from typing import Optional, List
from uuid import UUID

import httpx
import qrcode
from PIL import Image, ImageDraw, ImageFont
from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from infrastructure.database import get_session
from domain.models import Condominium, Visitor
from domain.models.access_credential import AccessCredential
from domain.models.qr_token import QrToken
from domain.models.audit_log import AuditLog
from config import settings as app_settings

router = APIRouter()

ACCESS_POINTS = {"vehicular_entry", "vehicular_exit", "pedestrian"}


def get_tenant_id(x_tenant_id: UUID = Header(..., description="Tenant/Condominium ID")) -> UUID:
    return x_tenant_id


class IssueVisitQrRequest(BaseModel):
    resident_id: UUID = Field(description="Resident who issues the QR")

    visitor_name: str = Field(min_length=2)
    vehicle_plate: Optional[str] = None

    # time-window
    valid_from: Optional[datetime] = None
    valid_until: datetime

    # access scope
    allowed_access_points: List[str] = Field(default_factory=lambda: ["vehicular_entry", "vehicular_exit", "pedestrian"])

    # single vs multi-use
    max_uses: Optional[int] = Field(default=None, description="1=single-use; NULL=unlimited within validity window")

    authorization_type: str = Field(default="guest")  # airbnb | employee | guest | delivery


class IssueVisitQrResponse(BaseModel):
    visitor_id: UUID
    credential_id: UUID
    qr_token_id: UUID

    token: str
    token_url: str
    expires_at: datetime

    # convenience: return a branded PNG card
    card_png_base64: str


async def _get_condo(session: AsyncSession, tenant_id: UUID) -> Condominium:
    res = await session.execute(select(Condominium).where(Condominium.id == tenant_id))
    condo = res.scalar_one_or_none()
    if not condo:
        raise HTTPException(status_code=404, detail="Condominium not found")
    return condo


def _validate_access_points(points: List[str]) -> List[str]:
    cleaned: List[str] = []
    for p in points:
        if p not in ACCESS_POINTS:
            raise HTTPException(status_code=400, detail=f"Invalid access point: {p}")
        cleaned.append(p)
    # de-dupe while preserving order
    out: List[str] = []
    for p in cleaned:
        if p not in out:
            out.append(p)
    return out


def _make_qr_png(data: str) -> bytes:
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _token_url(token: str) -> str:
    base = (app_settings.public_base_url or "").rstrip("/")
    return f"{base}/qr/{token}"


def _load_logo_bytes() -> Optional[bytes]:
    # Packaged logo (default). In production we can load per-tenant from Supabase Storage URL.
    import os

    path = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "branding", "sitnova", "logo.jpg")
    path = os.path.abspath(path)
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return f.read()


async def _maybe_fetch_logo_from_settings(condo: Condominium) -> Optional[bytes]:
    # If settings.branding.logo_url exists, prefer it.
    try:
        settings = condo.settings or {}
        branding = settings.get("branding") or {}
        logo_url = branding.get("logo_url")
        if not logo_url:
            return _load_logo_bytes()

        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(str(logo_url))
            if r.status_code == 200 and r.content:
                return r.content
    except Exception:
        pass

    return _load_logo_bytes()


def _render_card(
    *,
    condo_name: str,
    visitor_name: str,
    valid_until: datetime,
    allowed_access_points: List[str],
    qr_png: bytes,
    logo_bytes: Optional[bytes],
) -> bytes:
    # Basic card layout 1200x700
    W, H = 1200, 700
    bg = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(bg)

    # Fonts (fallback to default)
    try:
        font_title = ImageFont.truetype("DejaVuSans-Bold.ttf", 48)
        font_body = ImageFont.truetype("DejaVuSans.ttf", 28)
        font_small = ImageFont.truetype("DejaVuSans.ttf", 22)
    except Exception:
        font_title = ImageFont.load_default()
        font_body = ImageFont.load_default()
        font_small = ImageFont.load_default()

    margin = 40

    # Logo
    if logo_bytes:
        try:
            logo = Image.open(io.BytesIO(logo_bytes)).convert("RGBA")
            # fit into 260x120
            logo.thumbnail((260, 120))
            bg.paste(logo, (W - margin - logo.width, margin), logo)
        except Exception:
            pass

    # Title: Condominium name
    draw.text((margin, margin), condo_name, fill=(20, 20, 20), font=font_title)

    # Subtitle: visitor
    y = margin + 70
    draw.text((margin, y), f"Visitante: {visitor_name}", fill=(30, 30, 30), font=font_body)

    y += 45
    draw.text((margin, y), f"Válido hasta: {valid_until.strftime('%d/%m/%Y %H:%M')}", fill=(30, 30, 30), font=font_body)

    y += 45
    points = ", ".join(allowed_access_points)
    draw.text((margin, y), f"Accesos: {points}", fill=(30, 30, 30), font=font_small)

    # QR (right side)
    qr_img = Image.open(io.BytesIO(qr_png)).convert("RGBA")
    qr_img.thumbnail((420, 420))
    qr_x = W - margin - qr_img.width
    qr_y = H - margin - qr_img.height
    bg.paste(qr_img, (qr_x, qr_y), qr_img)

    # Footer branding
    footer = "Powered by SITNOVA SECURITY"
    draw.text((margin, H - margin - 30), footer, fill=(90, 90, 90), font=font_small)

    out = io.BytesIO()
    bg.save(out, format="PNG")
    return out.getvalue()


@router.post("/issue-visit", response_model=IssueVisitQrResponse)
async def issue_visit_qr(
    req: IssueVisitQrRequest,
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """Issue a visitor QR (branded card).

    Creates:
    - visitors row (approved)
    - access_credentials row (type=qr)
    - qr_tokens row (token + ttl)
    - audit_logs row

    NOTE: We intentionally do not support destructive operations here.
    """

    allowed = _validate_access_points(req.allowed_access_points)

    now = datetime.utcnow()
    valid_from = req.valid_from or now
    if req.valid_until <= valid_from:
        raise HTTPException(status_code=400, detail="valid_until must be after valid_from")

    # Create visitor
    visitor = Visitor(
        condominium_id=tenant_id,
        resident_id=req.resident_id,
        name=req.visitor_name,
        vehicle_plate=req.vehicle_plate,
        valid_until=req.valid_until,
        authorization_type=req.authorization_type,
        allowed_access_points=allowed,
        authorized_by="resident",
        status="approved",
        notes="Issued via QR",
    )
    session.add(visitor)
    await session.flush()

    # Create credential
    credential = AccessCredential(
        condominium_id=tenant_id,
        resident_id=req.resident_id,
        visitor_id=visitor.id,
        credential_type="qr",
        allowed_access_points=allowed,
        valid_from=valid_from,
        valid_until=req.valid_until,
        max_uses=req.max_uses,
        provisioning_mode="device",  # target: eventually provision into Hikvision
        device_target={},
        extra_data={"flow": "issue_visit_qr"},
    )
    session.add(credential)
    await session.flush()

    # Create token
    token = secrets.token_urlsafe(24)
    qr = QrToken(
        condominium_id=tenant_id,
        resident_id=req.resident_id,
        visitor_id=visitor.id,
        credential_id=credential.id,
        token=token,
        allowed_access_points=allowed,
        expires_at=req.valid_until,
        max_uses=req.max_uses,
        extra_data={"visitor_name": req.visitor_name},
    )
    session.add(qr)

    # Audit
    audit = AuditLog(
        condominium_id=tenant_id,
        actor_type="resident",
        actor_id=str(req.resident_id),
        actor_label=None,
        action="issue_qr",
        resource_type="qr_token",
        resource_id=qr.id,
        status="success",
        message="QR issued",
        extra_data={
            "visitor_id": str(visitor.id),
            "credential_id": str(credential.id),
            "allowed_access_points": allowed,
            "expires_at": req.valid_until.isoformat(),
            "max_uses": req.max_uses,
        },
    )
    session.add(audit)

    # Render card
    condo = await _get_condo(session, tenant_id)
    qr_url = _token_url(token)
    qr_png = _make_qr_png(qr_url)
    logo_bytes = await _maybe_fetch_logo_from_settings(condo)
    card_png = _render_card(
        condo_name=condo.name,
        visitor_name=req.visitor_name,
        valid_until=req.valid_until,
        allowed_access_points=allowed,
        qr_png=qr_png,
        logo_bytes=logo_bytes,
    )

    card_b64 = base64.b64encode(card_png).decode("ascii")

    await session.commit()

    return IssueVisitQrResponse(
        visitor_id=visitor.id,
        credential_id=credential.id,
        qr_token_id=qr.id,
        token=token,
        token_url=qr_url,
        expires_at=req.valid_until,
        card_png_base64=card_b64,
    )
