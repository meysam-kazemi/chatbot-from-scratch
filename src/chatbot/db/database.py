from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from chatbot.config import settings


SessionFactory = async_sessionmaker[AsyncSession]


def sqlalchemy_url(database_url: str) -> str:
    url = database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    return url.replace("postgresql://", "postgresql+psycopg://", 1)


@asynccontextmanager
async def database_session_factory() -> AsyncIterator[SessionFactory]:
    engine = create_async_engine(sqlalchemy_url(settings.database_url))
    try:
        yield async_sessionmaker(engine, expire_on_commit=False)
    finally:
        await engine.dispose()
