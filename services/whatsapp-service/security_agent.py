"""
Resident Assistant Agent - AI Conversational Agent for WhatsApp
Handles conversations with REGISTERED RESIDENTS of the condominium
Bilingual: Spanish and English
"""
from openai import AsyncOpenAI
from typing import Optional, Dict, Any, List
import structlog

from config import settings

logger = structlog.get_logger()
client = AsyncOpenAI(
    api_key=settings.OPENAI_API_KEY,
    base_url="https://openrouter.ai/api/v1"
)

# Conversation memory (in production, use Redis)
conversations: Dict[str, List[Dict[str, str]]] = {}

SYSTEM_PROMPT_RESIDENT = """Eres el asistente virtual de seguridad para residentes de "Residencial Sitnova".

CONTEXTO IMPORTANTE:
- Estás hablando con un RESIDENTE REGISTRADO del condominio
- Ya conoces su nombre y número de casa (se te proporcionará abajo)
- NO necesitas preguntarle quién es ni su número de casa
- El residente usa WhatsApp para gestionar visitas y hacer consultas

TUS FUNCIONES PARA RESIDENTES:
1. Ayudar a autorizar visitantes ("Viene Juan en 10 minutos")
2. Abrir puerta remotamente ("Abrir puerta")
3. Crear reportes de mantenimiento/seguridad ("Reportar: luz fundida")
4. Consultar historial de visitas ("¿Quién vino hoy?")
5. Responder preguntas generales sobre el condominio

REGLAS CRÍTICAS:
- NUNCA preguntes el nombre del residente - YA LO SABES
- NUNCA preguntes el número de casa - YA LO SABES
- Si mencionan que "viene alguien", ese alguien es el VISITANTE que viene A VISITAR al residente
- Sé conciso y directo (máximo 2-3 oraciones)
- Responde en el idioma que use el residente (español o inglés)
- Si no entiendes qué quieren, muestra las opciones disponibles

EJEMPLO CORRECTO:
Residente dice: "Viene Juan en 10 minutos"
Respuesta: "Perfecto, he registrado a Juan como visitante autorizado. Te notificaré cuando llegue."

EJEMPLO INCORRECTO (NUNCA hagas esto):
Residente dice: "Viene Juan en 10 minutos"
Respuesta: "¿Cuál es tu nombre y número de casa?" ← INCORRECTO, ya conoces al residente

INFORMACIÓN DEL CONDOMINIO:
- Nombre: Residencial Sitnova
- Ubicación: Costa Rica
- Seguridad: 24/7
"""


async def get_agent_response(
    phone: str,
    message: str,
    resident_info: Optional[Dict[str, Any]] = None
) -> str:
    """
    Get AI agent response for a message

    Args:
        phone: Sender's phone number
        message: User's message
        resident_info: Resident data if registered (name, unit, etc.)

    Returns:
        Agent's response text
    """
    try:
        # Get or create conversation history
        if phone not in conversations:
            conversations[phone] = []

        history = conversations[phone]

        # Build system prompt with resident context
        if resident_info:
            resident_context = f"""

DATOS DEL RESIDENTE (ya los conoces, NO preguntar):
- Nombre: {resident_info.get('name', 'Residente')}
- Casa/Unidad: {resident_info.get('unit', 'N/A')}

Saluda usando su nombre si es apropiado."""

            system_content = SYSTEM_PROMPT_RESIDENT + resident_context
        else:
            # This shouldn't happen in WhatsApp flow (unregistered handled elsewhere)
            system_content = SYSTEM_PROMPT_RESIDENT

        # Build messages
        messages = [
            {"role": "system", "content": system_content}
        ]

        # Add conversation history (last 10 messages)
        messages.extend(history[-10:])

        # Add current message
        messages.append({"role": "user", "content": message})

        # Call OpenAI (via OpenRouter)
        response = await client.chat.completions.create(
            model="openai/gpt-4o-mini",
            messages=messages,
            max_tokens=300,
            temperature=0.7
        )

        assistant_message = response.choices[0].message.content

        # Update conversation history
        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": assistant_message})

        # Keep only last 20 messages
        if len(history) > 20:
            conversations[phone] = history[-20:]

        logger.info(
            "agent_response_generated",
            phone=phone[-4:],
            is_resident=resident_info is not None,
            resident_name=resident_info.get('name') if resident_info else None,
            message_preview=message[:50],
            response_preview=assistant_message[:50]
        )

        return assistant_message

    except Exception as e:
        logger.error("agent_response_error", error=str(e), phone=phone[-4:])

        # Fallback response for residents
        if resident_info:
            return (
                f"Hola {resident_info.get('name', '')}, disculpa tuve un problema técnico. "
                "¿Podrías intentar de nuevo?\n\n"
                "Puedes decirme:\n"
                "• \"Viene [nombre]\" - autorizar visitante\n"
                "• \"Abrir puerta\" - apertura remota\n"
                "• \"Reportar: [problema]\" - crear reporte"
            )
        else:
            return (
                "Disculpa, tuve un problema técnico. Por favor intenta de nuevo.\n\n"
                "Sorry, I had a technical issue. Please try again."
            )


def clear_conversation(phone: str) -> None:
    """Clear conversation history for a phone number"""
    if phone in conversations:
        del conversations[phone]
        logger.info("conversation_cleared", phone=phone[-4:])
