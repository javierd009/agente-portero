"""Public QR landing/validation endpoint.

This is meant to be accessed by scanning a QR code.
It validates the token and shows a simple status page.

Important:
- Does NOT open gates automatically (security).
- Writes to audit_logs for traceability.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from infrastructure.database import get_session
from domain.models.qr_token import QrToken
from domain.models.access_credential import AccessCredential
from domain.models.audit_log import AuditLog

router = APIRouter()


def _page(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang='es'>
<head>
  <meta charset='utf-8'/>
  <meta name='viewport' content='width=device-width, initial-scale=1'/>
  <title>{title}</title>
  <style>
    body {{ font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial; margin: 0; background:#0b1220; color:#eef2ff; }}
    .card {{ max-width: 720px; margin: 40px auto; background:#111a2e; border:1px solid #223055; border-radius: 16px; padding: 24px; }}
    .muted {{ color:#b7c2e0; }}
    .ok {{ color:#58d68d; }}
    .bad {{ color:#ff6b6b; }}
    code {{ background:#0b1220; padding:2px 6px; border-radius: 8px; }}
  </style>
</head>
<body>
  <div class='card'>
    {body}
    <p class='muted' style='margin-top:24px'>Este evento queda registrado en la bitácora.</p>
  </div>
</body>
</html>"""


@router.get("/qr/{token}", response_class=HTMLResponse)
async def qr_landing(token: str, session: AsyncSession = Depends(get_session)):
    # Find token
    res = await session.execute(select(QrToken).where(QrToken.token == token))
    qr = res.scalar_one_or_none()
    if not qr:
        return HTMLResponse(_page("QR inválido", "<h2 class='bad'>QR inválido</h2><p>No existe o fue eliminado.</p>"), status_code=404)

    now = datetime.utcnow()

    # Fetch credential if linked
    credential = None
    if qr.credential_id:
        cres = await session.execute(select(AccessCredential).where(AccessCredential.id == qr.credential_id))
        credential = cres.scalar_one_or_none()

    # Determine status
    if qr.revoked_at:
        status = "revoked"
    elif qr.expires_at <= now:
        status = "expired"
    elif qr.max_uses is not None and qr.use_count >= qr.max_uses:
        status = "used"
    else:
        status = "active"

    # Audit scan
    audit = AuditLog(
        condominium_id=qr.condominium_id,
        actor_type="system",
        actor_id=None,
        actor_label="qr_landing",
        action="scan_qr",
        resource_type="qr_token",
        resource_id=qr.id,
        status="success",
        message=f"scan status={status}",
        extra_data={
            "token_id": str(qr.id),
            "credential_id": str(qr.credential_id) if qr.credential_id else None,
            "status": status,
        },
    )
    session.add(audit)
    await session.commit()

    if status == "active":
        body = f"""
        <h2 class='ok'>QR válido</h2>
        <p>Accesos permitidos: <code>{', '.join(qr.allowed_access_points or [])}</code></p>
        <p>Vence: <code>{qr.expires_at.strftime('%d/%m/%Y %H:%M')}</code></p>
        """
        return HTMLResponse(_page("QR válido", body), status_code=200)

    if status == "revoked":
        return HTMLResponse(_page("QR revocado", "<h2 class='bad'>QR revocado</h2><p>Este QR fue revocado.</p>"), status_code=410)

    if status == "expired":
        return HTMLResponse(_page("QR vencido", "<h2 class='bad'>QR vencido</h2><p>Este QR ya venció.</p>"), status_code=410)

    return HTMLResponse(_page("QR usado", "<h2 class='bad'>QR usado</h2><p>Este QR ya alcanzó su límite de usos.</p>"), status_code=410)
