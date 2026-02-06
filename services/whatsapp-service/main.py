"""
WhatsApp Service - Evolution API Integration
Handles bidirectional WhatsApp communication for Agente Portero
"""
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import structlog
from contextlib import asynccontextmanager

from config import settings
from webhook_handler import webhook_handler
from evolution_client import evolution_client

# Setup structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    logger.info(
        "whatsapp_service_starting",
        port=settings.PORT,
        instance=settings.EVOLUTION_INSTANCE
    )

    # Check Evolution API connection
    try:
        status = await evolution_client.get_instance_status()
        logger.info("evolution_api_connected", status=status)
    except Exception as e:
        logger.error("evolution_api_connection_failed", error=str(e))

    yield

    # Shutdown
    logger.info("whatsapp_service_stopping")


app = FastAPI(
    title="Agente Portero - WhatsApp Service",
    description="Bidirectional WhatsApp communication via Evolution API",
    version="0.1.0",
    lifespan=lifespan
)


@app.get("/health")
async def health_check():
    """Health check endpoint - returns healthy even if Evolution API is not connected"""
    evolution_status = "unknown"
    evolution_error = None

    try:
        # Try to verify Evolution API connection (optional)
        status = await evolution_client.get_instance_status()
        evolution_status = status.get("state", "connected")
    except Exception as e:
        evolution_status = "disconnected"
        evolution_error = str(e)
        # Log but don't fail - instance might not exist yet
        logger.warning("evolution_api_not_available", error=str(e))

    # Service is healthy as long as FastAPI is running
    # Evolution API connection is optional (instance can be created later)
    return {
        "status": "healthy",
        "service": "whatsapp-service",
        "evolution_api": evolution_status,
        "evolution_instance": settings.EVOLUTION_INSTANCE,
        "evolution_error": evolution_error
    }


@app.post("/webhook")
async def evolution_webhook(request: Request):
    """
    Webhook endpoint for Evolution API
    Receives incoming WhatsApp messages and events

    Configure this URL in Evolution API instance settings:
    POST https://your-domain.com/webhook
    """
    try:
        payload = await request.json()

        logger.debug("webhook_received", event_type=payload.get("event"))

        # Process message asynchronously
        await webhook_handler.process_message(payload)

        return {"status": "ok"}

    except Exception as e:
        logger.error("webhook_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/send-message")
async def send_message(
    phone: str,
    message: str,
    message_type: str = "text"
):
    """
    Send WhatsApp message (for testing or backend integration)

    Args:
        phone: Destination phone (5215512345678 format)
        message: Message text
        message_type: "text" | "buttons" | "media"
    """
    try:
        if message_type == "text":
            result = await evolution_client.send_text(phone, message)
        else:
            raise HTTPException(status_code=400, detail="Unsupported message type")

        return {"status": "sent", "result": result}

    except Exception as e:
        logger.error("send_message_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Agente Portero - WhatsApp Service",
        "version": "0.1.0",
        "instance": settings.EVOLUTION_INSTANCE,
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )
