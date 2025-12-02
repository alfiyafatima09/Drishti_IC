"""
Database connection and session management for Supabase/PostgreSQL.
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import text
from typing import AsyncGenerator, Optional
import logging

from backend.core.config import settings

logger = logging.getLogger(__name__)

# SQLAlchemy Base for models
Base = declarative_base()


def get_database_url() -> str:
    """Get database URL, converting to async format if needed."""
    url = settings.DATABASE_URL
    if not url:
        return ""
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url


# Lazy initialization of engine and session maker
_engine: Optional[object] = None
_async_session_maker: Optional[async_sessionmaker] = None


def get_engine():
    """Get or create the async engine."""
    global _engine
    if _engine is None:
        db_url = get_database_url()
        if not db_url:
            raise RuntimeError(
                "DATABASE_URL is not configured. "
                "Please set it in your .env file or environment variables.\n"
                "Example: DATABASE_URL=postgresql://postgres:password@db.xxx.supabase.co:5432/postgres"
            )
        _engine = create_async_engine(
            db_url,
            echo=settings.DEBUG,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
        )
    return _engine


def get_session_maker():
    """Get or create the session maker."""
    global _async_session_maker
    if _async_session_maker is None:
        _async_session_maker = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
    return _async_session_maker


# For backwards compatibility
@property
def engine():
    return get_engine()


@property  
def async_session_maker():
    return get_session_maker()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting async database sessions.
    Usage in FastAPI endpoints:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    session_maker = get_session_maker()
    async with session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """
    Initialize database - create tables if they don't exist.
    This runs the migration SQL to ensure all tables are present.
    """
    eng = get_engine()
    async with eng.begin() as conn:
        # Import models to register them with Base
        from backend.models import (
            ICSpecification,
            ScanHistory,
            DatasheetQueue,
            FakeRegistry,
            SyncJob,
            AppSettings,
        )
        
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created/verified successfully")


async def check_db_connection() -> bool:
    """Check if database connection is working."""
    try:
        eng = get_engine()
        async with eng.connect() as conn:
            await conn.execute(text("SELECT 1"))
            return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False


async def get_ic_count() -> int:
    """Get count of ICs in database."""
    try:
        session_maker = get_session_maker()
        async with session_maker() as session:
            result = await session.execute(
                text("SELECT COUNT(*) FROM ic_specifications")
            )
            return result.scalar() or 0
    except Exception:
        return 0
