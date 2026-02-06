"""Fast path command handling (no LLM, no conversation context).

Goal: near-instant response for operator-style commands like:
- abrir entrada
- abrir salida
- abrir peatonal

This module is intentionally deterministic and low-latency.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Literal, Optional

import httpx
import structlog

from config import settings

logger = structlog.get_logger()

DoorTarget = Literal[
    "vehicular_entry_panel",
    "vehicular_exit_panel",
    "pedestrian_gate",
    "vehicular_entry_biometric",
]


@dataclass(frozen=True)
class FastCommand:
    target: DoorTarget


_OPEN_PATTERNS: list[tuple[re.Pattern[str], DoorTarget]] = [
    # vehicular (panel)
    (re.compile(r"^\s*(abrir|abre)\s+(entrada|port[oó]n\s+entrada|port[oó]n\s+vehicular)\s*$", re.I), "vehicular_entry_panel"),
    (re.compile(r"^\s*(abrir|abre)\s+(salida|port[oó]n\s+salida)\s*$", re.I), "vehicular_exit_panel"),
    # pedestrian
    (re.compile(r"^\s*(abrir|abre)\s+(peatonal|peat[oó]n|puerta\s+peatonal)\s*$", re.I), "pedestrian_gate"),
    # force biometric for entry
    (re.compile(r"^\s*(abrir|abre)\s+(entrada)\s+(biom[eé]trico|biometrico)\s*$", re.I), "vehicular_entry_biometric"),
]

# simple in-memory debounce to avoid duplicate opens (per-process)
_last_open_ts: dict[DoorTarget, float] = {}


def parse_fast_command(text: str) -> Optional[FastCommand]:
    normalized = (text or "").strip()
    for pattern, target in _OPEN_PATTERNS:
        if pattern.match(normalized):
            return FastCommand(target=target)
    return None


async def execute_fast_open(target: DoorTarget) -> tuple[bool, str, dict]:
    """Execute the open command using direct ISAPI calls.

    Returns (success, user_message, log_context).
    """

    cooldown_s = getattr(settings, "FAST_OPEN_COOLDOWN_SECONDS", 4)
    now = time.time()
    last = _last_open_ts.get(target)
    if last and (now - last) < cooldown_s:
        return True, "Listo. Ya se estaba abriendo.", {"debounced": True}

    _last_open_ts[target] = now

    # Map targets to device IP + door index.
    if target == "vehicular_entry_panel":
        ip = settings.ACCESS_PANEL_IP
        door = 1
        xml_mode: Literal["strict", "legacy", "auto"] = "strict"
        access_point = "vehicular_entry"
        label = "Entrada"
    elif target == "vehicular_exit_panel":
        ip = settings.ACCESS_PANEL_IP
        door = 2
        xml_mode = "strict"
        access_point = "vehicular_exit"
        label = "Salida"
    elif target == "pedestrian_gate":
        ip = settings.PEDESTRIAN_DEVICE_IP
        door = 1
        xml_mode = "auto"
        access_point = "pedestrian"
        label = "Peatonal"
    elif target == "vehicular_entry_biometric":
        ip = settings.BIOMETRIC_ENTRY_IP
        door = 1
        xml_mode = "auto"
        access_point = "vehicular_entry"
        label = "Entrada (biométrico)"
    else:
        return False, "No configurado.", {"target": target}

    password = settings.HIK_PASS
    if target == "pedestrian_gate" and getattr(settings, "PEDESTRIAN_HIK_PASS", None):
        password = settings.PEDESTRIAN_HIK_PASS or password

    ok = await _isapi_open_door(
        ip=ip,
        door=door,
        username=settings.HIK_USER,
        password=password,
        xml_mode=xml_mode,
        timeout_s=getattr(settings, "FAST_OPEN_TIMEOUT_SECONDS", 1.5),
        retry_once=True,
    )

    log_ctx = {
        "access_point": access_point,
        "device_host": ip,
        "door_id": door,
        "success": bool(ok),
    }

    if ok:
        return True, f"Listo. {label} abierto.", log_ctx
    return False, f"No se pudo abrir {label}.", log_ctx


async def _isapi_open_door(
    *,
    ip: str,
    door: int,
    username: str,
    password: str,
    xml_mode: Literal["strict", "legacy", "auto"],
    timeout_s: float,
    retry_once: bool,
) -> bool:
    if not ip:
        logger.error("fast_open_missing_ip", door=door)
        return False

    url = f"http://{ip}/ISAPI/AccessControl/RemoteControl/door/{door}"

    strict_xml = (
        "<RemoteControlDoor version='2.0' xmlns='http://www.isapi.org/ver20/XMLSchema'>"
        "<cmd>open</cmd>"
        "</RemoteControlDoor>"
    )
    legacy_xml = "<RemoteControlDoor><cmd>open</cmd></RemoteControlDoor>"

    if xml_mode == "strict":
        bodies = [strict_xml]
    elif xml_mode == "legacy":
        bodies = [legacy_xml]
    else:
        bodies = [strict_xml, legacy_xml]

    auth = httpx.DigestAuth(username, password)

    async with httpx.AsyncClient(timeout=timeout_s, auth=auth) as client:
        for attempt in range(2 if retry_once else 1):
            for body in bodies:
                try:
                    resp = await client.put(
                        url,
                        content=body.encode("utf-8"),
                        headers={"Content-Type": "application/xml"},
                    )

                    if resp.status_code in (200, 201, 204):
                        logger.info("fast_open_ok", ip=ip, door=door, status=resp.status_code)
                        return True

                    logger.warn(
                        "fast_open_bad_status",
                        ip=ip,
                        door=door,
                        status=resp.status_code,
                        text=(resp.text[:200] if resp.text else ""),
                    )
                except (httpx.TimeoutException, httpx.ConnectError) as e:
                    logger.warn("fast_open_network_error", ip=ip, door=door, error=str(e))
                except Exception as e:
                    logger.exception("fast_open_error", ip=ip, door=door, error=str(e))

    return False
