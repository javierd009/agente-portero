"""
Voice Agent Tools
Functions that the AI agent can call during a conversation
"""
import logging
from typing import Any, Dict, Optional
import httpx

from config import Settings

logger = logging.getLogger(__name__)

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
    try:
        params = {"tenant_id": tenant_id} if tenant_id else {}

        if args.get("unit"):
            params["unit"] = args["unit"]
        if args.get("name"):
            params["name"] = args["name"]

        resp = await client.get(
            f"{base_url}/api/v1/residents/search",
            params=params,
            headers=headers
        )

        if resp.status_code == 200:
            data = resp.json()
            residents = data.get("residents", [])

            if residents:
                # Return simplified info (don't expose phone numbers, etc.)
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
            logger.warning(f"Backend returned {resp.status_code}: {resp.text}")
            return {"found": False, "message": "Error al buscar residente"}

    except Exception as e:
        logger.error(f"Error finding resident: {e}")
        return {"found": False, "error": str(e)}


async def check_preauthorized_visitor(
    client: httpx.AsyncClient,
    base_url: str,
    headers: dict,
    args: dict,
    tenant_id: Optional[str]
) -> dict:
    """Check if there's a pre-authorization for this visitor"""
    try:
        params = {"tenant_id": tenant_id} if tenant_id else {}

        if args.get("visitor_name"):
            params["visitor_name"] = args["visitor_name"]
        if args.get("resident_id"):
            params["resident_id"] = args["resident_id"]
        if args.get("unit"):
            params["unit"] = args["unit"]

        resp = await client.get(
            f"{base_url}/api/v1/authorizations/check",
            params=params,
            headers=headers
        )

        if resp.status_code == 200:
            data = resp.json()
            if data.get("authorized"):
                return {
                    "authorized": True,
                    "authorization_id": data.get("id"),
                    "resident_name": data.get("resident_name"),
                    "expires_at": data.get("expires_at"),
                    "message": f"Visitante pre-autorizado por {data.get('resident_name')}"
                }
            else:
                return {
                    "authorized": False,
                    "message": "No hay autorización previa para este visitante"
                }
        else:
            return {"authorized": False, "message": "No se encontró autorización previa"}

    except Exception as e:
        logger.error(f"Error checking pre-authorization: {e}")
        return {"authorized": False, "error": str(e)}


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
            headers=headers
        )

        if resp.status_code in (200, 201):
            data = resp.json()
            return {
                "sent": True,
                "request_id": data.get("id"),
                "message": "Solicitud de autorización enviada al residente por WhatsApp",
                "waiting_response": True
            }
        else:
            return {
                "sent": False,
                "message": "No se pudo enviar la solicitud al residente"
            }

    except Exception as e:
        logger.error(f"Error requesting authorization: {e}")
        return {"sent": False, "error": str(e)}


async def open_gate(
    client: httpx.AsyncClient,
    base_url: str,
    headers: dict,
    args: dict,
    tenant_id: Optional[str]
) -> dict:
    """Open the access gate"""
    try:
        payload = {
            "tenant_id": tenant_id,
            "visitor_name": args["visitor_name"],
            "resident_id": args.get("resident_id"),
            "authorization_type": args.get("authorization_type", "realtime"),
            "source": "voice_agent"
        }

        resp = await client.post(
            f"{base_url}/api/v1/gates/open",
            json=payload,
            headers=headers
        )

        if resp.status_code in (200, 201):
            return {
                "success": True,
                "message": "Puerta abierta exitosamente"
            }
        else:
            logger.warning(f"Gate open failed: {resp.status_code} - {resp.text}")
            return {
                "success": False,
                "message": "Error al abrir la puerta, contactando a guardia"
            }

    except Exception as e:
        logger.error(f"Error opening gate: {e}")
        return {"success": False, "error": str(e)}


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
        payload = {
            "tenant_id": tenant_id,
            "visitor_name": args["visitor_name"],
            "resident_id": args.get("resident_id"),
            "unit": args.get("unit"),
            "status": args["status"],
            "notes": args.get("notes"),
            "source": "voice_agent"
        }

        resp = await client.post(
            f"{base_url}/api/v1/visits/log",
            json=payload,
            headers=headers
        )

        if resp.status_code in (200, 201):
            return {
                "logged": True,
                "visit_id": resp.json().get("id"),
                "message": "Visita registrada en bitácora"
            }
        else:
            return {"logged": False, "message": "Error al registrar visita"}

    except Exception as e:
        logger.error(f"Error logging visit: {e}")
        return {"logged": False, "error": str(e)}
