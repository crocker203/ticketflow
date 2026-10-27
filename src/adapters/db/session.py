from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from src.config import settings
from src.adapters.db.models import Base


engine = create_async_engine(
    settings.database_url,
    echo=settings.DEBUG,
    pool_size=10,
    max_overflow=20,
)

async_session_maker = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for yielding an async database session per request."""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """Initialize tables in the database."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
