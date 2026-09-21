"""PostgreSQL-backed conversation memory."""

from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager

from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from chatbot.config import settings


def _postgres_dsn(database_url: str) -> str:
    return database_url.replace("postgresql+asyncpg://", "postgresql://", 1)


@contextmanager
def postgres_memory(
    database_url: str = settings.database_url,
) -> Iterator[PostgresSaver]:
    """Open sync PostgreSQL memory and create its tables when needed."""
    with PostgresSaver.from_conn_string(_postgres_dsn(database_url)) as memory:
        memory.setup()
        yield memory


@asynccontextmanager
async def async_postgres_memory(
    database_url: str = settings.database_url,
) -> AsyncIterator[AsyncPostgresSaver]:
    """Open async PostgreSQL memory and create its tables when needed."""
    async with AsyncPostgresSaver.from_conn_string(
        _postgres_dsn(database_url)
    ) as memory:
        await memory.setup()
        yield memory
