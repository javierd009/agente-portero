"""
NLP Intent Parser
Uses GPT-4 to understand user intentions from WhatsApp messages
"""
import json
from openai import AsyncOpenAI
from typing import Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime, timedelta
import structlog

from config import settings

logger = structlog.get_logger()
client = AsyncOpenAI(
    api_key=settings.OPENAI_API_KEY,
    base_url="https://openrouter.ai/api/v1"
)


# Intent schemas
class AuthorizeVisitorIntent(BaseModel):
    """Residente autoriza visitante"""
    intent: str = "authorize_visitor"
    visitor_name: str
    visitor_vehicle_plate: Optional[str] = None
    expected_time: Optional[str] = None
    valid_until: Optional[datetime] = None
    notes: Optional[str] = None


class OpenGateIntent(BaseModel):
    """Residente solicita abrir puerta"""
    intent: str = "open_gate"
    gate_name: Optional[str] = "main"
    urgency: str = "normal"


class CreateReportIntent(BaseModel):
    """Residente reporta incidente"""
    intent: str = "create_report"
    report_type: str
    description: str
    location: Optional[str] = None
    urgency: str = "normal"


class QueryLogsIntent(BaseModel):
    """Residente consulta logs"""
    intent: str = "query_logs"
    query_type: str
    visitor_name: Optional[str] = None
    date_range: Optional[str] = None


class UnknownIntent(BaseModel):
    """Intent no reconocido"""
    intent: str = "unknown"
    original_message: str


SYSTEM_PROMPT = """Eres un asistente que analiza mensajes de WhatsApp de RESIDENTES de un condominio.
Los residentes ya están identificados por su número de teléfono. Tu trabajo es detectar qué quieren hacer.

IMPORTANTE: El remitente SIEMPRE es un residente registrado. Cuando dicen "viene X", X es el VISITANTE, no el residente.

INTENTS SOPORTADOS:

1. **authorize_visitor**: Residente avisa que viene un visitante A SU CASA
   - "Viene Juan Pérez en 10 minutos" → visitor_name="Juan Pérez"
   - "Autorizar a María García" → visitor_name="María García"
   - "Viene un Uber placa ABC-123" → visitor_name="Uber", visitor_vehicle_plate="ABC-123"
   - "Va a llegar el plomero" → visitor_name="plomero"

2. **open_gate**: Residente pide abrir puerta remotamente
   - "Abrir puerta"
   - "Abre la entrada"
   - "Abrir portón"

3. **create_report**: Residente reporta un problema
   - "Reportar: luz fundida en estacionamiento"
   - "Hay una fuga de agua"
   - "Mucho ruido en la casa 5"

4. **query_logs**: Residente consulta historial de visitas
   - "¿Quién vino hoy?"
   - "Mostrar visitas de la semana"
   - "¿Pasó Juan ayer?"

Usa la función apropiada para clasificar el mensaje."""

# Tools definition (modern format)
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "authorize_visitor",
            "description": "El residente autoriza la entrada de un visitante a su casa",
            "parameters": {
                "type": "object",
                "properties": {
                    "visitor_name": {
                        "type": "string",
                        "description": "Nombre del visitante que viene (NO del residente)"
                    },
                    "visitor_vehicle_plate": {
                        "type": "string",
                        "description": "Placa del vehículo del visitante, si se menciona"
                    },
                    "expected_time": {
                        "type": "string",
                        "description": "Tiempo de llegada esperado (ej: 'en 10 minutos', 'a las 3pm')"
                    },
                    "notes": {
                        "type": "string",
                        "description": "Notas adicionales sobre el visitante"
                    }
                },
                "required": ["visitor_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "open_gate",
            "description": "El residente solicita abrir puerta/portón remotamente",
            "parameters": {
                "type": "object",
                "properties": {
                    "gate_name": {
                        "type": "string",
                        "enum": ["main", "pedestrian", "parking"],
                        "description": "Tipo de puerta a abrir"
                    },
                    "urgency": {
                        "type": "string",
                        "enum": ["normal", "urgent"],
                        "description": "Urgencia de la solicitud"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_report",
            "description": "El residente reporta un problema o incidente",
            "parameters": {
                "type": "object",
                "properties": {
                    "report_type": {
                        "type": "string",
                        "enum": ["maintenance", "security", "noise", "other"],
                        "description": "Tipo de reporte"
                    },
                    "description": {
                        "type": "string",
                        "description": "Descripción del problema"
                    },
                    "location": {
                        "type": "string",
                        "description": "Ubicación del problema"
                    },
                    "urgency": {
                        "type": "string",
                        "enum": ["normal", "urgent"],
                        "description": "Urgencia del reporte"
                    }
                },
                "required": ["description", "report_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_logs",
            "description": "El residente consulta historial de accesos/visitas",
            "parameters": {
                "type": "object",
                "properties": {
                    "query_type": {
                        "type": "string",
                        "enum": ["today", "yesterday", "week", "visitor"],
                        "description": "Período de consulta"
                    },
                    "visitor_name": {
                        "type": "string",
                        "description": "Nombre de visitante específico a buscar"
                    },
                    "date_range": {
                        "type": "string",
                        "description": "Rango de fechas personalizado"
                    }
                },
                "required": ["query_type"]
            }
        }
    }
]


async def parse_intent(
    message: str,
    context: Optional[Dict[str, Any]] = None
) -> BaseModel:
    """
    Parse user message to extract intent and parameters

    Args:
        message: User's WhatsApp message
        context: Optional conversation context

    Returns:
        Parsed intent object (one of the Intent models)
    """
    try:
        # Build messages
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Mensaje del residente: {message}"}
        ]

        if context:
            messages.insert(1, {
                "role": "system",
                "content": f"Contexto: {json.dumps(context, ensure_ascii=False)}"
            })

        # Call with tools (modern format)
        response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            temperature=0.1
        )

        # Extract tool call
        message_obj = response.choices[0].message

        if message_obj.tool_calls and len(message_obj.tool_calls) > 0:
            tool_call = message_obj.tool_calls[0]
            function_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)

            # Map function to intent model
            intent_map = {
                "authorize_visitor": AuthorizeVisitorIntent,
                "open_gate": OpenGateIntent,
                "create_report": CreateReportIntent,
                "query_logs": QueryLogsIntent
            }

            intent_class = intent_map.get(function_name)
            if intent_class:
                # Calculate valid_until for visitor authorization
                if function_name == "authorize_visitor":
                    valid_until = datetime.utcnow() + timedelta(
                        seconds=settings.DEFAULT_AUTHORIZATION_TTL
                    )
                    arguments["valid_until"] = valid_until

                intent_obj = intent_class(**arguments)
                logger.info(
                    "intent_parsed",
                    intent=function_name,
                    params=arguments
                )
                return intent_obj

        # Fallback: unknown intent
        logger.warning("intent_unknown", message=message)
        return UnknownIntent(original_message=message)

    except Exception as e:
        logger.error("intent_parse_error", error=str(e), message=message)
        return UnknownIntent(original_message=message)
