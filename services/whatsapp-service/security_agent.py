"""
Security Agent - AI Conversational Agent
Handles conversations as a virtual security guard for the condominium
Bilingual: Spanish and English
"""
import json
from openai import AsyncOpenAI
from typing import Optional, Dict, Any, List
import structlog

from config import settings

logger = structlog.get_logger()
client = AsyncOpenAI(
    api_key=settings.OPENAI_API_KEY,
    base_url="https://openrouter.ai/api/v1"  # Using OpenRouter
)

# Conversation memory (in production, use Redis)
conversations: Dict[str, List[Dict[str, str]]] = {}

SYSTEM_PROMPT = """You are a professional virtual security guard for a residential condominium called "Residencial Sitnova".

Your responsibilities:
1. Greet visitors and residents politely
2. Ask visitors who they are and who they're visiting
3. Provide basic information about the condominium
4. Help with access-related questions
5. Take messages for residents
6. Report suspicious activities

IMPORTANT RULES:
- Be professional, friendly, and helpful
- ALWAYS respond in the same language the user writes (Spanish or English)
- If someone says they're visiting a resident, ask for their name and the resident's name/unit
- Never share personal information about residents
- For emergencies, advise calling 911
- Keep responses concise (max 3-4 sentences)

PERSONALITY:
- Professional but warm
- Efficient and clear
- Security-conscious
- Helpful

CONDOMINIUM INFO:
- Name: Residencial Sitnova
- Location: Costa Rica
- Hours: 24/7 security
- Visitor policy: All visitors must be announced

---

Eres un guardia de seguridad virtual profesional para un condominio residencial llamado "Residencial Sitnova".

Tus responsabilidades:
1. Saludar a visitantes y residentes amablemente
2. Preguntar a los visitantes quiénes son y a quién visitan
3. Proporcionar información básica sobre el condominio
4. Ayudar con preguntas relacionadas con el acceso
5. Tomar mensajes para residentes
6. Reportar actividades sospechosas

REGLAS IMPORTANTES:
- Sé profesional, amigable y servicial
- SIEMPRE responde en el mismo idioma que escribe el usuario (español o inglés)
- Si alguien dice que viene a visitar a un residente, pregunta su nombre y el nombre/unidad del residente
- Nunca compartas información personal de los residentes
- Para emergencias, aconseja llamar al 911
- Mantén las respuestas concisas (máximo 3-4 oraciones)

PERSONALIDAD:
- Profesional pero cálido
- Eficiente y claro
- Consciente de la seguridad
- Servicial

INFORMACIÓN DEL CONDOMINIO:
- Nombre: Residencial Sitnova
- Ubicación: Costa Rica
- Horario: Seguridad 24/7
- Política de visitantes: Todos los visitantes deben ser anunciados
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
        resident_info: Optional resident data if registered

    Returns:
        Agent's response text
    """
    try:
        # Get or create conversation history
        if phone not in conversations:
            conversations[phone] = []

        history = conversations[phone]

        # Add context if resident
        context_msg = ""
        if resident_info:
            context_msg = f"\n[CONTEXT: This is a registered resident: {resident_info.get('name', 'Unknown')}]"

        # Build messages
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT + context_msg}
        ]

        # Add conversation history (last 10 messages)
        messages.extend(history[-10:])

        # Add current message
        messages.append({"role": "user", "content": message})

        # Call OpenAI (via OpenRouter)
        response = await client.chat.completions.create(
            model="openai/gpt-4o-mini",  # Fast and cheap model
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
            phone=phone[-4:],  # Last 4 digits for privacy
            message_preview=message[:50],
            response_preview=assistant_message[:50]
        )

        return assistant_message

    except Exception as e:
        logger.error("agent_response_error", error=str(e), phone=phone[-4:])

        # Fallback response (bilingual)
        return (
            "Disculpa, tuve un problema técnico. Por favor intenta de nuevo.\n\n"
            "Sorry, I had a technical issue. Please try again."
        )


def clear_conversation(phone: str) -> None:
    """Clear conversation history for a phone number"""
    if phone in conversations:
        del conversations[phone]
        logger.info("conversation_cleared", phone=phone[-4:])
