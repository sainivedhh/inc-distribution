"""Async Database Engine and Session Management."""

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from core.config import settings
from core.models import Base

# Database URL adjustment for asyncpg / aiosqlite
db_url = settings.DATABASE_URL
if db_url.startswith("sqlite:///"):
    db_url = db_url.replace("sqlite:///", "sqlite+aiosqlite:///")

engine = create_async_engine(db_url, echo=settings.DEBUG)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    async with async_session_maker() as session:
        yield session
