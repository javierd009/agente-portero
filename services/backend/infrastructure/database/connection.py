"""Database connection and session management"""
import os
from typing import AsyncGenerator, Optional
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlalchemy.orm import sessionmaker

# Lazy initialization - engine created on first use
_engine: Optional[AsyncEngine] = None
_async_session_maker: Optional[sessionmaker] = None


def _get_database_url() -> str:
    """Get and normalize DATABASE_URL"""
    url = os.getenv("DATABASE_URL", "")

    if not url:
        raise RuntimeError(
            "DATABASE_URL environment variable is not set. "
            "Please configure it in your .env file."
        )

    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://") and "+asyncpg" not in url:
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

    return url


def get_engine() -> AsyncEngine:
    """Get or create the async engine (lazy initialization)"""
    global _engine

    if _engine is None:
        _engine = create_async_engine(
            _get_database_url(),
            echo=os.getenv("DEBUG", "false").lower() == "true",
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
        )

    return _engine


def get_session_maker() -> sessionmaker:
    """Get or create the session maker (lazy initialization)"""
    global _async_session_maker

    if _async_session_maker is None:
        _async_session_maker = sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )

    return _async_session_maker


async def init_db() -> None:
    """Initialize database - create tables if not exist"""
    from domain.models import (
        Condominium, Agent, Resident, Visitor,
        Vehicle, AccessLog, CameraEvent, Notification
    )

    async with get_engine().begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting async database session"""
    async with get_session_maker()() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
