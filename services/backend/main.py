"""
Agente Portero - Backend API
FastAPI + SQLModel + Supabase (Multi-tenant)
"""
from dotenv import load_dotenv
load_dotenv()  # Load .env before any other imports

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from api.v1 import (
    agents,
    access,
    notifications,
    camera_events,
    cameras,
    condominiums,
    gates,
    residents,
    visitors,
    reports,
)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    import logging
    logger = logging.getLogger(__name__)

    # Las tablas ya existen en Supabase (creadas en FASE 1)
    # No necesitamos create_all(), la conexión será lazy
    logger.info("Backend API started successfully")

    yield

    # Shutdown
    logger.info("Backend API shutting down")

app = FastAPI(
    title="Agente Portero API",
    description="API para sistema de guardia virtual multi-condominio",
    version="0.1.0",
    lifespan=lifespan
)

# CORS - Permitir dominios de produccion y desarrollo
ALLOWED_ORIGINS = [
    "https://agente-portero.vercel.app",
    "https://dashboard-portero.vercel.app",
    *[f"http://localhost:{port}" for port in range(3000, 3007)],
    *[f"http://127.0.0.1:{port}" for port in range(3000, 3007)],
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=r"https://.*\.vercel\.app",  # All Vercel preview deployments
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(condominiums.router, prefix="/api/v1/condominiums", tags=["condominiums"])
app.include_router(agents.router, prefix="/api/v1/agents", tags=["agents"])
app.include_router(residents.router, prefix="/api/v1/residents", tags=["residents"])
app.include_router(visitors.router, prefix="/api/v1/visitors", tags=["visitors"])
app.include_router(access.router, prefix="/api/v1/access", tags=["access"])
app.include_router(notifications.router, prefix="/api/v1/notifications", tags=["notifications"])
app.include_router(camera_events.router, prefix="/api/v1/camera-events", tags=["camera-events"])
app.include_router(cameras.router, prefix="/api/v1/cameras", tags=["cameras"])
app.include_router(gates.router, prefix="/api/v1/gates", tags=["gates"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["reports"])

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "agente-portero-backend"}

@app.get("/")
async def root():
    return {"message": "Agente Portero API", "docs": "/docs"}
