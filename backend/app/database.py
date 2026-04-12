from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


def _build_async_url() -> str:
    """Ensure DATABASE_URL uses asyncpg driver and has SSL for external hosts."""
    url = settings.database_url
    # Ensure asyncpg driver
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgresql+psycopg2://"):
        url = url.replace("postgresql+psycopg2://", "postgresql+asyncpg://")
    # Note: asyncpg uses ssl=require param, not sslmode
    # Supabase URLs work with asyncpg if we add ssl=require
    if "localhost" not in url and "ssl" not in url:
        sep = "&" if "?" in url else "?"
        url += f"{sep}ssl=require"
    return url


engine = create_async_engine(_build_async_url(), echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with async_session() as session:
        yield session
