import uuid
from datetime import datetime, timezone

from psycopg import errors
from psycopg.rows import class_row
from psycopg_pool import AsyncConnectionPool

from chatbot.db.models.user import User


async def create_user(
    pool: AsyncConnectionPool, email: str, password_hash: str
) -> User | None:
    user_id = uuid.uuid4()
    try:
        async with pool.connection() as connection, connection.cursor(
            row_factory=class_row(User)
        ) as cursor:
            await cursor.execute(
                """INSERT INTO users (id, email, password_hash)
                   VALUES (%s, %s, %s)
                   RETURNING id, email, password_hash, is_active, created_at""",
                (user_id, email, password_hash),
            )
            return await cursor.fetchone()
    except errors.UniqueViolation:
        return None


async def get_user_by_email(pool: AsyncConnectionPool, email: str) -> User | None:
    async with pool.connection() as connection, connection.cursor(
        row_factory=class_row(User)
    ) as cursor:
        await cursor.execute(
            """SELECT id, email, password_hash, is_active, created_at
               FROM users WHERE email = %s""",
            (email,),
        )
        return await cursor.fetchone()


async def get_user(pool: AsyncConnectionPool, user_id: uuid.UUID) -> User | None:
    async with pool.connection() as connection, connection.cursor(
        row_factory=class_row(User)
    ) as cursor:
        await cursor.execute(
            """SELECT id, email, password_hash, is_active, created_at
               FROM users WHERE id = %s""",
            (user_id,),
        )
        return await cursor.fetchone()


async def store_refresh_token(
    pool: AsyncConnectionPool,
    token_hash: str,
    user_id: uuid.UUID,
    expires_at: datetime,
) -> None:
    async with pool.connection() as connection:
        await connection.execute(
            """INSERT INTO refresh_tokens (token_hash, user_id, expires_at)
               VALUES (%s, %s, %s)""",
            (token_hash, user_id, expires_at),
        )


async def consume_refresh_token(
    pool: AsyncConnectionPool, token_hash: str, user_id: uuid.UUID
) -> bool:
    async with pool.connection() as connection:
        cursor = await connection.execute(
            """DELETE FROM refresh_tokens
               WHERE token_hash = %s AND user_id = %s AND expires_at > %s""",
            (token_hash, user_id, datetime.now(timezone.utc)),
        )
        return cursor.rowcount == 1


async def revoke_refresh_token(
    pool: AsyncConnectionPool, token_hash: str
) -> None:
    async with pool.connection() as connection:
        await connection.execute(
            "DELETE FROM refresh_tokens WHERE token_hash = %s", (token_hash,)
        )
