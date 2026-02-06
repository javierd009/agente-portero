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
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
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
from infrastructure.hikvision.client import HikvisionGateClient
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

    # What the visitor will present to the biometric reader (encoded in the QR image)
    card_no: str
    employee_no: str

    # Legacy fields (kept for compatibility)
    token: str
    token_url: str
    expires_at: datetime

    provisioned: bool
    provisioned_devices: List[str] = Field(default_factory=list)

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


def _to_naive_utc(dt: datetime) -> datetime:
    """Normalize datetime for DB columns defined as TIMESTAMP WITHOUT TIME ZONE.

    If an aware datetime is provided, convert to UTC and drop tzinfo.
    If naive, assume it's already in UTC.
    """
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def _format_local(dt: datetime, tz: str) -> str:
    z = ZoneInfo(tz)
    if dt.tzinfo is None:
        # assume already local
        local = dt.replace(tzinfo=z)
    else:
        local = dt.astimezone(z)
    # ISAPI expects local string without offset
    return local.replace(tzinfo=None).strftime("%Y-%m-%dT%H:%M:%S")


def _random_digits(n: int) -> str:
    # Avoid leading zeros being dropped by consumers; still allowed.
    alphabet = "0123456789"
    return "".join(secrets.choice(alphabet) for _ in range(n))


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
    card_no: str,
    qr_png: bytes,
    logo_bytes: Optional[bytes],
) -> bytes:
    # Recommended vertical card layout for better biometric QR scanning
    # 1080x1920 (phone-friendly)
    W, H = 1080, 1920
    bg = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(bg)

    # Fonts (fallback to default)
    try:
        font_title = ImageFont.truetype("DejaVuSans-Bold.ttf", 58)
        font_body = ImageFont.truetype("DejaVuSans.ttf", 40)
        font_small = ImageFont.truetype("DejaVuSans.ttf", 30)
        font_code = ImageFont.truetype("DejaVuSans-Bold.ttf", 56)
    except Exception:
        font_title = ImageFont.load_default()
        font_body = ImageFont.load_default()
        font_small = ImageFont.load_default()
        font_code = ImageFont.load_default()

    margin = 60

    # Header
    draw.text((margin, margin), condo_name, fill=(20, 20, 20), font=font_title)

    # Optional logo (top-right)
    if logo_bytes:
        try:
            logo = Image.open(io.BytesIO(logo_bytes)).convert("RGBA")
            logo.thumbnail((260, 140))
            bg.paste(logo, (W - margin - logo.width, margin), logo)
        except Exception:
            pass

    # QR centered and large
    qr_img = Image.open(io.BytesIO(qr_png)).convert("RGBA")

    # Target QR size ~70% of width (big, reliable)
    target = int(W * 0.78)
    qr_img = qr_img.resize((target, target))

    qr_x = (W - qr_img.width) // 2
    qr_y = 260  # space for header
    bg.paste(qr_img, (qr_x, qr_y), qr_img)

    # Footer details
    y = qr_y + qr_img.height + 80
    draw.text((margin, y), f"Visitante: {visitor_name}", fill=(30, 30, 30), font=font_body)

    y += 60
    draw.text((margin, y), f"Válido hasta: {valid_until.strftime('%d/%m/%Y %H:%M')}", fill=(30, 30, 30), font=font_body)

    y += 70
    draw.text((margin, y), "Código:", fill=(60, 60, 60), font=font_small)
    y += 38
    draw.text((margin, y), str(card_no), fill=(10, 10, 10), font=font_code)

    # Branding small at bottom
    footer = "Powered by SITNOVA SECURITY"
    draw.text((margin, H - margin - 40), footer, fill=(120, 120, 120), font=font_small)

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

    # Normalize datetimes (avoid mixing tz-aware vs tz-naive with TIMESTAMP WITHOUT TIME ZONE)
    valid_from_in = req.valid_from or now
    valid_from = _to_naive_utc(valid_from_in)
    valid_until = _to_naive_utc(req.valid_until)

    if valid_until <= valid_from:
        raise HTTPException(status_code=400, detail="valid_until must be after valid_from")

    # Create visitor
    visitor = Visitor(
        condominium_id=tenant_id,
        resident_id=req.resident_id,
        name=req.visitor_name,
        vehicle_plate=req.vehicle_plate,
        valid_until=valid_until,
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
        valid_until=valid_until,
        max_uses=req.max_uses,
        provisioning_mode="device",  # target: eventually provision into Hikvision
        device_target={},
        extra_data={"flow": "issue_visit_qr"},
    )
    session.add(credential)
    await session.flush()

    # --- Provision QR credential into biometrics (.1 and .136) ---
    # employeeNo must be unique per device; we keep it human-readable.
    employee_no = f"{app_settings.qr_employee_prefix}{visitor.id.hex[:10]}"

    # cardNo must be numeric and (ideally) non-repeating.
    # We'll attempt a few times in case of collisions.
    card_no: Optional[str] = None
    provisioned_devices: List[str] = []
    provisioned_ok = False

    begin_time_local = _format_local(valid_from, app_settings.condo_timezone)
    end_time_local = _format_local(valid_until, app_settings.condo_timezone)

    for _ in range(10):
        candidate = _random_digits(int(app_settings.qr_card_digits))

        bio1 = HikvisionGateClient(
            host=app_settings.hik_bio1_host,
            port=app_settings.hik_bio1_port,
            username=app_settings.hik_user,
            password=app_settings.hik_bio1_password,
        )
        bio2 = HikvisionGateClient(
            host=app_settings.hik_bio2_host,
            port=app_settings.hik_bio2_port,
            username=app_settings.hik_user,
            password=app_settings.hik_bio2_password,
        )

        r1 = await bio1.create_user_and_card(
            employee_no=employee_no,
            name=req.visitor_name,
            begin_time=begin_time_local,
            end_time=end_time_local,
            card_no=candidate,
        )
        r2 = await bio2.create_user_and_card(
            employee_no=employee_no,
            name=req.visitor_name,
            begin_time=begin_time_local,
            end_time=end_time_local,
            card_no=candidate,
        )

        # If provisioning fails, try another card number.
        if r1.get("success") and r2.get("success"):
            card_no = candidate
            provisioned_ok = True
            provisioned_devices = [app_settings.hik_bio1_host, app_settings.hik_bio2_host]
            break

    if not provisioned_ok or not card_no:
        raise HTTPException(status_code=502, detail="Failed to provision QR credential into biometric devices")

    # Create token row for auditing/ops (not the QR payload presented to the reader)
    token = secrets.token_urlsafe(24)
    qr = QrToken(
        condominium_id=tenant_id,
        resident_id=req.resident_id,
        visitor_id=visitor.id,
        credential_id=credential.id,
        token=token,
        allowed_access_points=allowed,
        expires_at=valid_until,
        max_uses=req.max_uses,
        extra_data={
            "visitor_name": req.visitor_name,
            "employee_no": employee_no,
            "card_no": card_no,
            "provisioned_devices": provisioned_devices,
        },
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
        status="success" if provisioned_ok else "failure",
        message="QR issued and provisioned to biometrics",
        extra_data={
            "visitor_id": str(visitor.id),
            "credential_id": str(credential.id),
            "allowed_access_points": allowed,
            "expires_at": valid_until.isoformat(),
            "max_uses": req.max_uses,
            "employee_no": employee_no,
            "card_no": card_no,
            "provisioned_devices": provisioned_devices,
        },
    )
    session.add(audit)

    # Render card: QR encodes card_no (what the visitor presents)
    condo = await _get_condo(session, tenant_id)
    qr_png = _make_qr_png(card_no)
    logo_bytes = await _maybe_fetch_logo_from_settings(condo)
    card_png = _render_card(
        condo_name=condo.name,
        visitor_name=req.visitor_name,
        valid_until=valid_until,
        allowed_access_points=allowed,
        card_no=card_no,
        qr_png=qr_png,
        logo_bytes=logo_bytes,
    )

    card_b64 = base64.b64encode(card_png).decode("ascii")

    await session.commit()

    return IssueVisitQrResponse(
        visitor_id=visitor.id,
        credential_id=credential.id,
        qr_token_id=qr.id,
        card_no=card_no,
        employee_no=employee_no,
        token=token,
        token_url=_token_url(token),
        expires_at=valid_until,
        provisioned=provisioned_ok,
        provisioned_devices=provisioned_devices,
        card_png_base64=card_b64,
    )
