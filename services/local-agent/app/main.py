import os
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
import httpx

app = FastAPI(title="portero-local-agent", version="0.1.0")

LOCAL_AGENT_KEY = os.getenv("LOCAL_AGENT_KEY", "")

# Actions -> ISAPI targets
# NOTE: keep creds out of code in prod; for MVP we allow env-based creds per device.
ACTIONS = {
    "vehicular_in": {
        "host": os.getenv("ACS_PANEL_HOST", "172.20.22.3"),
        "user": os.getenv("ACS_PANEL_USER", "admin"),
        "pass": os.getenv("ACS_PANEL_PASS", ""),
        "door": 1,
        "xml": "<RemoteControlDoor version='2.0' xmlns='http://www.isapi.org/ver20/XMLSchema'><cmd>open</cmd></RemoteControlDoor>",
    },
    "vehicular_out": {
        "host": os.getenv("ACS_PANEL_HOST", "172.20.22.3"),
        "user": os.getenv("ACS_PANEL_USER", "admin"),
        "pass": os.getenv("ACS_PANEL_PASS", ""),
        "door": 2,
        "xml": "<RemoteControlDoor version='2.0' xmlns='http://www.isapi.org/ver20/XMLSchema'><cmd>open</cmd></RemoteControlDoor>",
    },
    "vehicular_backup": {
        "host": os.getenv("BIO_VEH_HOST", "172.20.22.136"),
        "user": os.getenv("BIO_VEH_USER", "admin"),
        "pass": os.getenv("BIO_VEH_PASS", ""),
        "door": 1,
        "xml": "<RemoteControlDoor><cmd>open</cmd></RemoteControlDoor>",
    },
    "peatonal": {
        "host": os.getenv("BIO_PED_HOST", "172.20.22.1"),
        "user": os.getenv("BIO_PED_USER", "admin"),
        "pass": os.getenv("BIO_PED_PASS", ""),
        "door": 1,
        "xml": "<RemoteControlDoor><cmd>open</cmd></RemoteControlDoor>",
    },
}


class OpenReq(BaseModel):
    action: str


class AcsQuery(BaseModel):
    # Which device to query
    device: str = "bio_vehicular"  # bio_vehicular | panel | bio_peatonal
    # How many events
    limit: int = 5
    # Filters
    card_only: bool = True
    card_no: str | None = None
    employee_no: str | None = None
    name: str | None = None

    # Optional time window (ISO-8601). If omitted, defaults to last 48h.
    start_time: str | None = None
    end_time: str | None = None


@app.get("/health")
async def health():
    return {"ok": True}


def require_key(x_local_agent_key: str | None):
    if not LOCAL_AGENT_KEY:
        # Allow running without key for local-only testing.
        return
    if not x_local_agent_key or x_local_agent_key != LOCAL_AGENT_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")


@app.post("/open")
async def open_gate(req: OpenReq, x_local_agent_key: str | None = Header(default=None)):
    require_key(x_local_agent_key)

    cfg = ACTIONS.get(req.action)
    if not cfg:
        raise HTTPException(status_code=400, detail="Unknown action")

    host = cfg["host"]
    user = cfg["user"]
    pwd = cfg["pass"]
    door = cfg["door"]
    xml = cfg["xml"]

    if not pwd:
        raise HTTPException(status_code=500, detail=f"Missing password for action {req.action}")

    url = f"http://{host}/ISAPI/AccessControl/RemoteControl/door/{door}"

    auth = httpx.DigestAuth(user, pwd)
    async with httpx.AsyncClient(timeout=8) as client:
        r = await client.put(url, auth=auth, headers={"Content-Type": "application/xml"}, content=xml)

    ok = r.status_code in (200, 204)
    # Never return raw XML to callers (operators/WhatsApp). Keep it internal.
    return {"ok": ok, "status": r.status_code, "action": req.action}


def _acs_device_cfg(device: str) -> dict:
    device = (device or "").strip().lower()
    if device in ("bio_vehicular", "biometrico", "136"):
        return {
            "host": os.getenv("BIO_VEH_HOST", "172.20.22.136"),
            "user": os.getenv("BIO_VEH_USER", "admin"),
            "pass": os.getenv("BIO_VEH_PASS", ""),
        }
    if device in ("bio_peatonal", "peatonal", "1"):
        return {
            "host": os.getenv("BIO_PED_HOST", "172.20.22.1"),
            "user": os.getenv("BIO_PED_USER", "admin"),
            "pass": os.getenv("BIO_PED_PASS", ""),
        }
    # default: panel
    return {
        "host": os.getenv("ACS_PANEL_HOST", "172.20.22.3"),
        "user": os.getenv("ACS_PANEL_USER", "admin"),
        "pass": os.getenv("ACS_PANEL_PASS", ""),
    }


@app.post("/acs/last")
async def acs_last(req: AcsQuery, x_local_agent_key: str | None = Header(default=None)):
    """Fetch recent access control events (read-only)."""
    require_key(x_local_agent_key)

    limit = int(req.limit or 5)
    if limit < 1:
        limit = 1
    if limit > 30:
        limit = 30

    cfg = _acs_device_cfg(req.device)
    if not cfg.get("pass"):
        raise HTTPException(status_code=500, detail="Missing device password")

    from datetime import datetime, timedelta, timezone

    # Default time window: last 48 hours (device typically requires a window for useful results)
    tz = timezone(timedelta(hours=-6))  # America/Costa_Rica
    now = datetime.now(tz)
    start = now - timedelta(hours=48)

    start_iso = req.start_time or start.isoformat(timespec="seconds")
    end_iso = req.end_time or now.isoformat(timespec="seconds")

    cond: dict = {
        "searchID": "1",
        "searchResultPosition": 0,
        "maxResults": limit,
        # Some firmwares require both major and minor fields to be present.
        "major": 0,
        "minor": 0,
        "startTime": start_iso,
        "endTime": end_iso,
        "timeReverseOrder": True,
    }

    # Optional filters
    if req.card_no:
        cond["cardNo"] = str(req.card_no)
    if req.employee_no:
        cond["employeeNoString"] = str(req.employee_no)
    if req.name:
        cond["name"] = str(req.name)

    url = f"http://{cfg['host']}/ISAPI/AccessControl/AcsEvent?format=json"
    auth = httpx.DigestAuth(cfg["user"], cfg["pass"])

    async def fetch(minor_val: int | None) -> list[dict]:
        q = dict(cond)
        if minor_val is not None:
            q["major"] = 5
            q["minor"] = int(minor_val)
        payload = {"AcsEventCond": q}
        async with httpx.AsyncClient(timeout=10) as client:
            rr = await client.post(url, auth=auth, json=payload)
        if rr.status_code not in (200, 201):
            raise HTTPException(status_code=502, detail=f"Device error ({rr.status_code})")
        dd = rr.json() if rr.content else {}
        return (((dd.get("AcsEvent") or {}).get("InfoList")) or [])

    # If card_only is requested, pull from likely card-related minors and merge.
    # This avoids returning door open/close operations that don't include cardNo.
    minor_candidates = [1, 9, 75, 76, 10, 11, 12, 13]

    raw_events: list[dict] = []
    if req.card_only and not (req.card_no or req.employee_no or req.name):
        for mv in minor_candidates:
            raw_events.extend([e for e in await fetch(mv) if isinstance(e, dict)])
            # stop early if we already have enough card events
            card_hits = [e for e in raw_events if e.get("cardNo")]
            if len(card_hits) >= limit:
                raw_events = card_hits
                break
    else:
        raw_events = [e for e in await fetch(None) if isinstance(e, dict)]

    # Normalize to a clean list
    out: list[dict] = []
    for e in raw_events:
        # Card-only filter: requires cardNo present
        if req.card_only and not e.get("cardNo"):
            continue
        out.append({
            "time": e.get("time"),
            "doorNo": e.get("doorNo"),
            "cardNo": e.get("cardNo"),
            "name": e.get("name"),
            "employeeNoString": e.get("employeeNoString"),
            "currentVerifyMode": e.get("currentVerifyMode"),
            "major": e.get("major"),
            "minor": e.get("minor"),
            "serialNo": e.get("serialNo"),
        })

    # Sort by time desc when available
    out.sort(key=lambda x: x.get("time") or "", reverse=True)

    return {
        "ok": True,
        "device": req.device,
        "returned": len(out[:limit]),
        "events": out[:limit],
    }
