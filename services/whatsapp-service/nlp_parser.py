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
    base_url="https://openrouter.ai/api/v1"  # Using OpenRouter
)


# Intent schemas
class AuthorizeVisitorIntent(BaseModel):
    """Residente autoriza visitante"""
    intent: str = "authorize_visitor"
    visitor_name: str
    visitor_vehicle_plate: Optional[str] = None
    expected_time: Optional[str] = None  # "en 10 minutos", "a las 14:00"
    valid_until: Optional[datetime] = None
    notes: Optional[str] = None


class OpenGateIntent(BaseModel):
    """Residente solicita abrir puerta"""
    intent: str = "open_gate"
    gate_name: Optional[str] = "main"  # "main", "pedestrian", "parking"
    urgency: str = "normal"  # "normal", "urgent"


class CreateReportIntent(BaseModel):
    """Residente reporta incidente"""
    intent: str = "create_report"
    report_type: str  # "maintenance", "security", "noise", "other"
    description: str
    location: Optional[str] = None
    urgency: str = "normal"


class QueryLogsIntent(BaseModel):
    """Residente consulta logs"""
    intent: str = "query_logs"
    query_type: str  # "today", "yesterday", "week", "visitor"
    visitor_name: Optional[str] = None
    date_range: Optional[str] = None


class UnknownIntent(BaseModel):
    """Intent no reconocido"""
    intent: str = "unknown"
    original_message: str


SYSTEM_PROMPT = """Eres un asistente de análisis de intenciones para un sistema de guardia virtual de condominios.

Analiza mensajes de WhatsApp de residentes y extrae la intención (intent) y parámetros relevantes.

INTENTS SOPORTADOS:

1. **authorize_visitor**: Residente avisa que viene un visitante
   Ejemplos:
   - "Viene Juan Pérez en 10 minutos"
   - "Autorizar a María García hasta las 6pm"
   - "Viene un Uber en auto gris placa ABC-123"

2. **open_gate**: Residente pide abrir puerta
   Ejemplos:
   - "Abrir puerta"
   - "Abre la entrada principal"
   - "Urgente: abrir puerta peatonal"

3. **create_report**: Residente reporta un problema
   Ejemplos:
   - "Reportar: luz fundida en estacionamiento"
   - "Hay un foco prendido en área común"
   - "Mucho ruido en la casa de al lado"

4. **query_logs**: Residente consulta historial
   Ejemplos:
   - "¿Quién vino hoy?"
   - "Mostrar visitas de la semana"
   - "¿Pasó Juan ayer?"

5. **unknown**: No coincide con ningún intent conocido

Responde SOLO con JSON válido siguiendo el schema del intent detectado.
"""


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
        # Build messages for GPT-4
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Mensaje: {message}"}
        ]

        if context:
            messages.insert(1, {
                "role": "system",
                "content": f"Contexto: {json.dumps(context, ensure_ascii=False)}"
            })

        # Call GPT-4 with function calling
        response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=messages,
            functions=[
                {
                    "name": "authorize_visitor",
                    "description": "Residente autoriza la entrada de un visitante",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "visitor_name": {"type": "string"},
                            "visitor_vehicle_plate": {"type": "string"},
                            "expected_time": {"type": "string"},
                            "notes": {"type": "string"}
                        },
                        "required": ["visitor_name"]
                    }
                },
                {
                    "name": "open_gate",
                    "description": "Residente solicita abrir puerta/portón",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "gate_name": {
                                "type": "string",
                                "enum": ["main", "pedestrian", "parking"]
                            },
                            "urgency": {
                                "type": "string",
                                "enum": ["normal", "urgent"]
                            }
                        }
                    }
                },
                {
                    "name": "create_report",
                    "description": "Residente reporta un problema o incidente",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "report_type": {
                                "type": "string",
                                "enum": ["maintenance", "security", "noise", "other"]
                            },
                            "description": {"type": "string"},
                            "location": {"type": "string"},
                            "urgency": {
                                "type": "string",
                                "enum": ["normal", "urgent"]
                            }
                        },
                        "required": ["description", "report_type"]
                    }
                },
                {
                    "name": "query_logs",
                    "description": "Residente consulta historial de accesos",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query_type": {
                                "type": "string",
                                "enum": ["today", "yesterday", "week", "visitor"]
                            },
                            "visitor_name": {"type": "string"},
                            "date_range": {"type": "string"}
                        },
                        "required": ["query_type"]
                    }
                }
            ],
            function_call="auto",
            temperature=0.1
        )

        # Extract function call
        message_obj = response.choices[0].message

        if message_obj.function_call:
            function_name = message_obj.function_call.name
            arguments = json.loads(message_obj.function_call.arguments)

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
