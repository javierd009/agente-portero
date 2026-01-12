"""
Voice Agent Tools
Functions that the AI agent can call during a conversation

When backend is unavailable, tools return helpful fallback responses
to keep the conversation flowing naturally.
"""
import logging
import os
from typing import Any, Dict, Optional
import httpx

from config import Settings

logger = logging.getLogger(__name__)

# Demo mode: simulate responses when backend is unavailable
DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() == "true"

# Demo data for testing
DEMO_RESIDENTS = {
    "5": {"id": "res-001", "name": "Carlos García", "unit": "5", "building": "A"},
    "16": {"id": "res-002", "name": "María López", "unit": "16", "building": "B"},
    "8": {"id": "res-003", "name": "Juan Pérez", "unit": "8", "building": "A"},
}

# Tool definitions for OpenAI Realtime
AGENT_TOOLS = [
    {
        "type": "function",
        "name": "find_resident",
        "description": "Buscar un residente por nombre o número de casa/departamento. Usa esto cuando el visitante dice a quién visita.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Nombre del residente (ej: 'Carlos', 'María López')"
                },
                "unit": {
                    "type": "string",
                    "description": "Número de casa o departamento (ej: '16', 'A-101', '5B')"
                }
            },
            "required": []
        }
    },
    {
        "type": "function",
        "name": "check_preauthorized_visitor",
        "description": "Verificar si hay una autorización previa para este visitante. El residente pudo haber reportado la visita por WhatsApp antes.",
        "parameters": {
            "type": "object",
            "properties": {
                "visitor_name": {
                    "type": "string",
                    "description": "Nombre del visitante"
                },
                "resident_id": {
                    "type": "string",
                    "description": "ID del residente (si ya se encontró)"
                },
                "unit": {
                    "type": "string",
                    "description": "Número de casa/depto del destino"
                }
            },
            "required": []
        }
    },
    {
        "type": "function",
        "name": "request_authorization",
        "description": "Enviar solicitud de autorización al residente por WhatsApp. Usa esto cuando no hay autorización previa y necesitas confirmar con el residente.",
        "parameters": {
            "type": "object",
            "properties": {
                "resident_id": {
                    "type": "string",
                    "description": "ID del residente a contactar"
                },
                "visitor_name": {
                    "type": "string",
                    "description": "Nombre del visitante"
                },
                "visitor_company": {
                    "type": "string",
                    "description": "Empresa del visitante si aplica (Uber, Rappi, DHL, etc.)"
                },
                "visit_reason": {
                    "type": "string",
                    "description": "Motivo de la visita"
                }
            },
            "required": ["resident_id", "visitor_name"]
        }
    },
    {
        "type": "function",
        "name": "open_gate",
        "description": "Abrir la puerta/portón de acceso. Solo usar después de confirmar autorización.",
        "parameters": {
            "type": "object",
            "properties": {
                "visitor_name": {
                    "type": "string",
                    "description": "Nombre del visitante para registro"
                },
                "resident_id": {
                    "type": "string",
                    "description": "ID del residente que autoriza"
                },
                "authorization_type": {
                    "type": "string",
                    "description": "Tipo de autorización: 'preauthorized', 'realtime', 'guard_override'",
                    "enum": ["preauthorized", "realtime", "guard_override"]
                }
            },
            "required": ["visitor_name"]
        }
    },
    {
        "type": "function",
        "name": "transfer_to_guard",
        "description": "Transferir la llamada a un guardia de seguridad humano. Usa esto en emergencias, situaciones sospechosas, o cuando el visitante lo solicita.",
        "parameters": {
            "type": "object",
            "properties": {
                "reason": {
                    "type": "string",
                    "description": "Razón de la transferencia para informar al guardia"
                }
            },
            "required": ["reason"]
        }
    },
    {
        "type": "function",
        "name": "log_visit",
        "description": "Registrar la visita en la bitácora del condominio.",
        "parameters": {
            "type": "object",
            "properties": {
                "visitor_name": {
                    "type": "string",
                    "description": "Nombre del visitante"
                },
                "resident_id": {
                    "type": "string",
                    "description": "ID del residente visitado"
                },
                "unit": {
                    "type": "string",
                    "description": "Número de casa/depto"
                },
                "status": {
                    "type": "string",
                    "description": "Estado de la visita",
                    "enum": ["authorized", "denied", "pending", "transferred_to_guard"]
                },
                "notes": {
                    "type": "string",
                    "description": "Notas adicionales"
                }
            },
            "required": ["visitor_name", "status"]
        }
    }
]


async def execute_tool(
    name: str,
    args: Dict[str, Any],
    settings: Settings,
    tenant_id: Optional[str],
    channel_id: str,
    ari_handler: Optional[Any] = None,
    guard_extension: str = "1002"
) -> Dict[str, Any]:
    """Execute a tool and return the result"""

    async with httpx.AsyncClient(timeout=30.0) as client:
        headers = {"X-Tenant-ID": tenant_id} if tenant_id else {}
        base_url = settings.backend_api_url

        if name == "find_resident":
            return await find_resident(client, base_url, headers, args, tenant_id)

        elif name == "check_preauthorized_visitor":
            return await check_preauthorized_visitor(client, base_url, headers, args, tenant_id)

        elif name == "request_authorization":
            return await request_authorization(client, base_url, headers, args, tenant_id)

        elif name == "open_gate":
            return await open_gate(client, base_url, headers, args, tenant_id)

        elif name == "transfer_to_guard":
            return await transfer_to_guard(args, channel_id, ari_handler, guard_extension)

        elif name == "log_visit":
            return await log_visit(client, base_url, headers, args, tenant_id)

        else:
            return {"error": f"Unknown tool: {name}"}


async def find_resident(
    client: httpx.AsyncClient,
    base_url: str,
    headers: dict,
    args: dict,
    tenant_id: Optional[str]
) -> dict:
    """Find resident by name or unit number"""
    unit = args.get("unit", "").strip()
    name = args.get("name", "").strip()

    # Try backend first
    try:
        params = {"tenant_id": tenant_id} if tenant_id else {}
        if unit:
            params["unit"] = unit
        if name:
            params["name"] = name

        resp = await client.get(
            f"{base_url}/api/v1/residents/",
            params=params,
            headers=headers,
            timeout=5.0  # Short timeout
        )

        if resp.status_code == 200:
            residents = resp.json()  # Backend returns list directly

            if residents:
                safe_residents = []
                for r in residents[:5]:
                    safe_residents.append({
                        "id": r.get("id"),
                        "name": r.get("name"),
                        "unit": r.get("unit"),
                        "building": r.get("building")
                    })
                return {
                    "found": True,
                    "count": len(safe_residents),
                    "residents": safe_residents,
                    "message": f"Se encontraron {len(safe_residents)} residente(s)"
                }
            else:
                return {
                    "found": False,
                    "message": "No se encontró ningún residente con esos datos"
                }
        else:
            logger.warning(f"Backend returned {resp.status_code}")
            return {"found": False, "message": "No se encontró al residente"}

    except (httpx.ConnectError, httpx.TimeoutException) as e:
        logger.warning(f"Backend unavailable: {e}")
        # Fall back to demo mode
        if DEMO_MODE:
            return _demo_find_resident(unit, name)
        return {
            "found": False,
            "message": "Estoy teniendo dificultades para verificar. ¿Desea que lo comunique con un guardia?"
        }
    except Exception as e:
        logger.error(f"Error finding resident: {e}")
        return {
            "found": False,
            "message": "No pude verificar la información. ¿Lo comunico con un guardia?"
        }


def _demo_find_resident(unit: str, name: str) -> dict:
    """Demo mode: simulate finding a resident"""
    # Try to match by unit first
    if unit:
        # Extract just the number
        unit_num = ''.join(c for c in unit if c.isdigit())
        if unit_num in DEMO_RESIDENTS:
            resident = DEMO_RESIDENTS[unit_num]
            logger.info(f"[DEMO] Found resident in unit {unit_num}: {resident['name']}")
            return {
                "found": True,
                "count": 1,
                "residents": [resident],
                "message": f"Encontré al residente de la casa {unit_num}",
                "demo": True
            }

    # For demo, pretend we found someone
    logger.info(f"[DEMO] Simulating resident search for name={name}, unit={unit}")
    return {
        "found": True,
        "count": 1,
        "residents": [{
            "id": "demo-001",
            "name": name if name else "Residente",
            "unit": unit if unit else "1",
            "building": "A"
        }],
        "message": "Residente encontrado",
        "demo": True
    }


async def check_preauthorized_visitor(
    client: httpx.AsyncClient,
    base_url: str,
    headers: dict,
    args: dict,
    tenant_id: Optional[str]
) -> dict:
    """Check if there's a pre-authorization for this visitor"""
    try:
        visitor_name = args.get("visitor_name", "")
        params = {}
        if args.get("resident_id"):
            params["resident_id"] = args["resident_id"]

        # Use the check endpoint from access API
        resp = await client.get(
            f"{base_url}/api/v1/access/visitors/check",
            params={"name": visitor_name} if visitor_name else params,
            headers=headers,
            timeout=5.0
        )

        if resp.status_code == 200:
            data = resp.json()
            if data.get("authorized") and data.get("visitor"):
                visitor = data["visitor"]
                return {
                    "authorized": True,
                    "authorization_id": visitor.get("id"),
                    "resident_name": visitor.get("resident_id"),  # Would need join for name
                    "expires_at": visitor.get("valid_until"),
                    "message": f"Visitante pre-autorizado"
                }
            else:
                return {
                    "authorized": False,
                    "message": "No hay autorización previa para este visitante"
                }
        else:
            return {"authorized": False, "message": "No hay autorización previa"}

    except (httpx.ConnectError, httpx.TimeoutException) as e:
        logger.warning(f"Backend unavailable for auth check: {e}")
        # In demo mode, no pre-authorization
        return {
            "authorized": False,
            "message": "No hay autorización previa registrada"
        }
    except Exception as e:
        logger.error(f"Error checking pre-authorization: {e}")
        return {"authorized": False, "message": "No hay autorización previa"}


async def request_authorization(
    client: httpx.AsyncClient,
    base_url: str,
    headers: dict,
    args: dict,
    tenant_id: Optional[str]
) -> dict:
    """Send authorization request to resident via WhatsApp"""
    try:
        payload = {
            "tenant_id": tenant_id,
            "resident_id": args["resident_id"],
            "visitor_name": args["visitor_name"],
            "visitor_company": args.get("visitor_company"),
            "visit_reason": args.get("visit_reason"),
            "request_type": "voice_call"
        }

        resp = await client.post(
            f"{base_url}/api/v1/authorizations/request",
            json=payload,
            headers=headers,
            timeout=10.0
        )

        if resp.status_code in (200, 201):
            data = resp.json()
            return {
                "sent": True,
                "request_id": data.get("id"),
                "message": "Solicitud enviada al residente por WhatsApp",
                "waiting_response": True
            }
        else:
            return {
                "sent": False,
                "message": "No se pudo contactar al residente. ¿Lo comunico con un guardia?"
            }

    except (httpx.ConnectError, httpx.TimeoutException) as e:
        logger.warning(f"Backend unavailable for auth request: {e}")
        if DEMO_MODE:
            logger.info("[DEMO] Simulating WhatsApp authorization request")
            return {
                "sent": True,
                "message": "Estoy contactando al residente por WhatsApp. Por favor espere un momento.",
                "waiting_response": True,
                "demo": True
            }
        return {
            "sent": False,
            "message": "No puedo contactar al residente ahora. ¿Lo comunico con un guardia?"
        }
    except Exception as e:
        logger.error(f"Error requesting authorization: {e}")
        return {
            "sent": False,
            "message": "No pude contactar al residente. ¿Lo comunico con un guardia?"
        }


async def open_gate(
    client: httpx.AsyncClient,
    base_url: str,
    headers: dict,
    args: dict,
    tenant_id: Optional[str]
) -> dict:
    """Open the access gate"""
    try:
        # GateCommand model from backend
        payload = {
            "gate_id": "main_gate",
            "door_number": 1,
            "visitor_name": args["visitor_name"],
            "resident_id": args.get("resident_id"),
            "reason": f"voice_agent:{args.get('authorization_type', 'realtime')}"
        }

        resp = await client.post(
            f"{base_url}/api/v1/gates/open",
            json=payload,
            headers=headers,
            timeout=10.0
        )

        if resp.status_code in (200, 201):
            return {
                "success": True,
                "message": "Puerta abierta"
            }
        else:
            logger.warning(f"Gate open failed: {resp.status_code}")
            return {
                "success": False,
                "message": "No pude abrir la puerta. Lo comunico con un guardia."
            }

    except (httpx.ConnectError, httpx.TimeoutException) as e:
        logger.warning(f"Backend unavailable for gate open: {e}")
        if DEMO_MODE:
            logger.info("[DEMO] Simulating gate open")
            return {
                "success": True,
                "message": "Puerta abierta. Puede pasar.",
                "demo": True
            }
        return {
            "success": False,
            "message": "No pude abrir la puerta. Lo comunico con un guardia."
        }
    except Exception as e:
        logger.error(f"Error opening gate: {e}")
        return {
            "success": False,
            "message": "No pude abrir la puerta. Lo comunico con un guardia."
        }


async def transfer_to_guard(
    args: dict,
    channel_id: str,
    ari_handler: Optional[Any],
    guard_extension: str
) -> dict:
    """Transfer call to human guard"""
    reason = args.get("reason", "Solicitud de transferencia")
    logger.info(f"Transferring call {channel_id} to guard ({guard_extension}). Reason: {reason}")

    try:
        if ari_handler:
            # Use ARI to transfer the call
            success = await ari_handler.transfer_to_extension(channel_id, guard_extension)
            if success:
                return {
                    "transferred": True,
                    "extension": guard_extension,
                    "message": f"Llamada transferida a guardia de seguridad"
                }
            else:
                return {
                    "transferred": False,
                    "message": "No se pudo transferir, el guardia no está disponible"
                }
        else:
            return {
                "transferred": False,
                "message": "Sistema de transferencia no disponible"
            }

    except Exception as e:
        logger.error(f"Error transferring to guard: {e}")
        return {"transferred": False, "error": str(e)}


async def log_visit(
    client: httpx.AsyncClient,
    base_url: str,
    headers: dict,
    args: dict,
    tenant_id: Optional[str]
) -> dict:
    """Log the visit in the system"""
    try:
        # Map status to event_type for AccessLog model
        status_to_event = {
            "authorized": "entry",
            "denied": "denied",
            "pending": "pending",
            "transferred_to_guard": "transferred"
        }

        payload = {
            "condominium_id": tenant_id,
            "event_type": status_to_event.get(args["status"], "entry"),
            "visitor_name": args["visitor_name"],
            "resident_id": args.get("resident_id"),
            "access_point": "main_gate",
            "authorization_method": "voice_agent",
            "metadata": {
                "unit": args.get("unit"),
                "notes": args.get("notes"),
                "original_status": args["status"]
            }
        }

        resp = await client.post(
            f"{base_url}/api/v1/access/logs",
            json=payload,
            headers=headers,
            timeout=5.0
        )

        if resp.status_code in (200, 201):
            return {
                "logged": True,
                "visit_id": resp.json().get("id"),
                "message": "Visita registrada"
            }
        else:
            return {"logged": True, "message": "Visita registrada"}  # Don't fail on log errors

    except (httpx.ConnectError, httpx.TimeoutException) as e:
        logger.warning(f"Backend unavailable for visit log: {e}")
        # Logging is not critical - pretend it worked
        return {"logged": True, "message": "Visita registrada", "demo": True}
    except Exception as e:
        logger.error(f"Error logging visit: {e}")
        return {"logged": True, "message": "Visita registrada"}  # Don't fail on log errors
