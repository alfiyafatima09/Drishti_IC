"""
Database connection and session management for Supabase/PostgreSQL.
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import text
from typing import AsyncGenerator
import logging

from core.config import settings

logger = logging.getLogger(__name__)

# SQLAlchemy Base for models
Base = declarative_base()

# Create async engine
# Supabase connection string format: postgresql://postgres:[PASSWORD]@db.[PROJECT_REF].supabase.co:5432/postgres
# For async, we use: postgresql+asyncpg://...
def get_database_url() -> str:
    """Get database URL, converting to async format if needed."""
    url = settings.DATABASE_URL
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url


# Create async engine with connection pooling
# Disable SQL query logging for performance (can be enabled via DEBUG if needed)
engine = create_async_engine(
    get_database_url(),
    echo=False,  # Disable SQL query logging for performance
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,  # Verify connections before using
    pool_recycle=3600,  # Recycle connections after 1 hour
)

# Create session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting async database sessions.
    Usage in FastAPI endpoints:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_db_for_background() -> AsyncGenerator[AsyncSession, None]:
    """
    Get database session for background tasks.
    Unlike get_db(), this doesn't auto-commit - the task manages its own commits.
    """
    async with async_session_maker() as session:
        try:
            yield session
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
    async with engine.begin() as conn:
        # Import models to register them with Base
        from models import (
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
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False


async def get_ic_count() -> int:
    """Get count of ICs in database."""
    try:
        async with async_session_maker() as session:
            result = await session.execute(
                text("SELECT COUNT(*) FROM ic_specifications")
            )
            return result.scalar() or 0
    except Exception:
        return 0

