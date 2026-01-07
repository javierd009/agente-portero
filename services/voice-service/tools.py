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
        "name": "check_visitor",
        "description": "Verificar si un visitante está pre-autorizado para entrar. Busca por nombre, placa de vehículo o número de identificación.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Nombre del visitante"
                },
                "plate": {
                    "type": "string",
                    "description": "Placa del vehículo"
                },
                "id_number": {
                    "type": "string",
                    "description": "Número de identificación (INE, pasaporte, etc.)"
                }
            },
            "required": []
        }
    },
    {
        "type": "function",
        "name": "find_resident",
        "description": "Buscar un residente por nombre o número de unidad/departamento",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Nombre del residente"
                },
                "unit": {
                    "type": "string",
                    "description": "Número de unidad o departamento (ej: A-101, 205)"
                }
            },
            "required": []
        }
    },
    {
        "type": "function",
        "name": "notify_resident",
        "description": "Notificar al residente sobre la llegada de un visitante via WhatsApp",
        "parameters": {
            "type": "object",
            "properties": {
                "resident_id": {
                    "type": "string",
                    "description": "ID del residente"
                },
                "visitor_name": {
                    "type": "string",
                    "description": "Nombre del visitante"
                },
                "visitor_plate": {
                    "type": "string",
                    "description": "Placa del vehículo del visitante (opcional)"
                }
            },
            "required": ["resident_id", "visitor_name"]
        }
    },
    {
        "type": "function",
        "name": "open_gate",
        "description": "Abrir la puerta de acceso principal",
        "parameters": {
            "type": "object",
            "properties": {
                "gate_id": {
                    "type": "string",
                    "description": "ID de la puerta a abrir (default: main_gate)"
                },
                "visitor_name": {
                    "type": "string",
                    "description": "Nombre del visitante para registro"
                },
                "resident_id": {
                    "type": "string",
                    "description": "ID del residente que recibe la visita"
                }
            },
            "required": ["visitor_name"]
        }
    },
    {
        "type": "function",
        "name": "get_recent_plates",
        "description": "Obtener las placas de vehículos detectadas recientemente por las cámaras",
        "parameters": {
            "type": "object",
            "properties": {
                "minutes": {
                    "type": "integer",
                    "description": "Minutos hacia atrás para buscar (default: 5)"
                }
            },
            "required": []
        }
    },
    {
        "type": "function",
        "name": "transfer_to_guard",
        "description": "Transferir la llamada a un guardia humano",
        "parameters": {
            "type": "object",
            "properties": {
                "reason": {
                    "type": "string",
                    "description": "Razón de la transferencia"
                }
            },
            "required": ["reason"]
        }
    },
    {
        "type": "function",
        "name": "register_visitor",
        "description": "Registrar un nuevo visitante en el sistema",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Nombre del visitante"
                },
                "resident_id": {
                    "type": "string",
                    "description": "ID del residente que recibe la visita"
                },
                "reason": {
                    "type": "string",
                    "description": "Motivo de la visita"
                },
                "vehicle_plate": {
                    "type": "string",
                    "description": "Placa del vehículo (opcional)"
                },
                "id_number": {
                    "type": "string",
                    "description": "Número de identificación (opcional)"
                }
            },
            "required": ["name", "resident_id", "reason"]
        }
    }
]


async def execute_tool(
    name: str,
    args: Dict[str, Any],
    settings: Settings,
    tenant_id: Optional[str],
    channel_id: str
) -> Dict[str, Any]:
    """Execute a tool and return the result"""

    async with httpx.AsyncClient() as client:
        headers = {"X-Tenant-ID": tenant_id} if tenant_id else {}
        base_url = settings.backend_api_url

        if name == "check_visitor":
            return await check_visitor(client, base_url, headers, args)

        elif name == "find_resident":
            return await find_resident(client, base_url, headers, args)

        elif name == "notify_resident":
            return await notify_resident(client, base_url, headers, args)

        elif name == "open_gate":
            return await open_gate(client, base_url, headers, args, tenant_id)

        elif name == "get_recent_plates":
            return await get_recent_plates(client, base_url, headers, args)

        elif name == "transfer_to_guard":
            return await transfer_to_guard(args, channel_id)

        elif name == "register_visitor":
            return await register_visitor(client, base_url, headers, args)

        else:
            return {"error": f"Unknown tool: {name}"}


async def check_visitor(
    client: httpx.AsyncClient,
    base_url: str,
    headers: dict,
    args: dict
) -> dict:
    """Check if visitor is pre-authorized"""
    params = {}
    if args.get("name"):
        params["name"] = args["name"]
    if args.get("plate"):
        params["plate"] = args["plate"]
    if args.get("id_number"):
        params["id_number"] = args["id_number"]

    if not params:
        return {"authorized": False, "message": "No se proporcionó información del visitante"}

    try:
        resp = await client.get(
            f"{base_url}/api/v1/access/visitors/check",
            params=params,
            headers=headers
        )
        if resp.status_code == 200:
            return resp.json()
        else:
            return {"authorized": False, "error": resp.text}
    except Exception as e:
        logger.error(f"Error checking visitor: {e}")
        return {"authorized": False, "error": str(e)}


async def find_resident(
    client: httpx.AsyncClient,
    base_url: str,
    headers: dict,
    args: dict
) -> dict:
    """Find resident by name or unit"""
    params = {}
    if args.get("unit"):
        params["unit"] = args["unit"]

    try:
        resp = await client.get(
            f"{base_url}/api/v1/access/residents",
            params=params,
            headers=headers
        )
        if resp.status_code == 200:
            residents = resp.json()

            # Filter by name if provided
            if args.get("name"):
                name_lower = args["name"].lower()
                residents = [
                    r for r in residents
                    if name_lower in r.get("name", "").lower()
                ]

            if residents:
                return {
                    "found": True,
                    "residents": residents[:5]  # Limit to 5 results
                }
            else:
                return {"found": False, "message": "No se encontró el residente"}
        else:
            return {"found": False, "error": resp.text}
    except Exception as e:
        logger.error(f"Error finding resident: {e}")
        return {"found": False, "error": str(e)}


async def notify_resident(
    client: httpx.AsyncClient,
    base_url: str,
    headers: dict,
    args: dict
) -> dict:
    """Notify resident about visitor arrival"""
    try:
        resp = await client.post(
            f"{base_url}/api/v1/notifications/visitor-arrival",
            params={
                "resident_id": args["resident_id"],
                "visitor_name": args["visitor_name"],
                "visitor_plate": args.get("visitor_plate")
            },
            headers=headers
        )
        if resp.status_code == 200:
            return resp.json()
        else:
            return {"sent": False, "error": resp.text}
    except Exception as e:
        logger.error(f"Error notifying resident: {e}")
        return {"sent": False, "error": str(e)}


async def open_gate(
    client: httpx.AsyncClient,
    base_url: str,
    headers: dict,
    args: dict,
    tenant_id: Optional[str]
) -> dict:
    """Open the access gate"""
    # First, log the access
    try:
        access_log = {
            "condominium_id": tenant_id,
            "event_type": "visitor_entry",
            "access_point": args.get("gate_id", "main_gate"),
            "visitor_name": args["visitor_name"],
            "authorization_method": "ai_agent",
            "resident_id": args.get("resident_id")
        }

        resp = await client.post(
            f"{base_url}/api/v1/access/logs",
            json=access_log,
            headers=headers
        )

        # TODO: Send command to Hikvision gate via backend
        # For now, we'll simulate success

        return {
            "success": True,
            "message": "Puerta abierta exitosamente",
            "access_log_id": resp.json().get("id") if resp.status_code == 201 else None
        }

    except Exception as e:
        logger.error(f"Error opening gate: {e}")
        return {"success": False, "error": str(e)}


async def get_recent_plates(
    client: httpx.AsyncClient,
    base_url: str,
    headers: dict,
    args: dict
) -> dict:
    """Get recently detected license plates"""
    try:
        params = {"minutes": args.get("minutes", 5)}
        resp = await client.get(
            f"{base_url}/api/v1/camera-events/plates/recent",
            params=params,
            headers=headers
        )
        if resp.status_code == 200:
            return resp.json()
        else:
            return {"plates": [], "error": resp.text}
    except Exception as e:
        logger.error(f"Error getting recent plates: {e}")
        return {"plates": [], "error": str(e)}


async def transfer_to_guard(args: dict, channel_id: str) -> dict:
    """Transfer call to human guard"""
    reason = args.get("reason", "Solicitud de transferencia")
    logger.info(f"Transferring call {channel_id} to guard. Reason: {reason}")

    # TODO: Implement actual call transfer via ARI
    # This would involve:
    # 1. Create a new channel to the guard extension
    # 2. Bridge the visitor channel with the guard channel
    # 3. Leave the Stasis app

    return {
        "transferred": True,
        "message": f"Transfiriendo a guardia de seguridad. Razón: {reason}"
    }


async def register_visitor(
    client: httpx.AsyncClient,
    base_url: str,
    headers: dict,
    args: dict
) -> dict:
    """Register a new visitor"""
    try:
        visitor_data = {
            "name": args["name"],
            "resident_id": args["resident_id"],
            "reason": args["reason"],
            "vehicle_plate": args.get("vehicle_plate"),
            "id_number": args.get("id_number"),
            "authorized_by": "ai_agent",
            "status": "approved"
        }

        resp = await client.post(
            f"{base_url}/api/v1/access/visitors",
            json=visitor_data,
            headers=headers
        )

        if resp.status_code == 201:
            return {
                "registered": True,
                "visitor_id": resp.json().get("id")
            }
        else:
            return {"registered": False, "error": resp.text}

    except Exception as e:
        logger.error(f"Error registering visitor: {e}")
        return {"registered": False, "error": str(e)}
