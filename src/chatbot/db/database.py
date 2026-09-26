from contextlib import asynccontextmanager

from psycopg_pool import AsyncConnectionPool

from chatbot.ai.memory import _postgres_dsn
from chatbot.config import settings


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY,
    email VARCHAR(320) NOT NULL UNIQUE,
    username VARCHAR(30),
    password_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
ALTER TABLE users ADD COLUMN IF NOT EXISTS username VARCHAR(30);
CREATE UNIQUE INDEX IF NOT EXISTS users_username_key
    ON users (LOWER(username)) WHERE username IS NOT NULL;
CREATE TABLE IF NOT EXISTS refresh_tokens (
    token_hash CHAR(64) PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS refresh_tokens_user_id_idx ON refresh_tokens(user_id);
"""


@asynccontextmanager
async def database_pool():
    pool = AsyncConnectionPool(_postgres_dsn(settings.database_url), open=False)
    await pool.open()
    try:
        async with pool.connection() as connection:
            await connection.execute(SCHEMA)
        yield pool
    finally:
        await pool.close()
