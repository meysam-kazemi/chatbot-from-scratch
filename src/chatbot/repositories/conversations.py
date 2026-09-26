import uuid

from psycopg.rows import class_row
from psycopg_pool import AsyncConnectionPool

from chatbot.db.models.conversation import Conversation


FIELDS = "id, user_id, title, created_at, updated_at"


async def create(
    pool: AsyncConnectionPool, user_id: uuid.UUID, title: str | None
) -> Conversation:
    async with pool.connection() as connection, connection.cursor(
        row_factory=class_row(Conversation)
    ) as cursor:
        await cursor.execute(
            f"""INSERT INTO conversations (id, user_id, title)
                VALUES (%s, %s, %s) RETURNING {FIELDS}""",
            (uuid.uuid4(), user_id, title),
        )
        return await cursor.fetchone()


async def list_for_user(
    pool: AsyncConnectionPool, user_id: uuid.UUID, limit: int, offset: int
) -> list[Conversation]:
    async with pool.connection() as connection, connection.cursor(
        row_factory=class_row(Conversation)
    ) as cursor:
        await cursor.execute(
            f"""SELECT {FIELDS} FROM conversations
                WHERE user_id = %s
                ORDER BY updated_at DESC LIMIT %s OFFSET %s""",
            (user_id, limit, offset),
        )
        return await cursor.fetchall()


async def get_for_user(
    pool: AsyncConnectionPool,
    conversation_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Conversation | None:
    async with pool.connection() as connection, connection.cursor(
        row_factory=class_row(Conversation)
    ) as cursor:
        await cursor.execute(
            f"SELECT {FIELDS} FROM conversations WHERE id = %s AND user_id = %s",
            (conversation_id, user_id),
        )
        return await cursor.fetchone()


async def update(
    pool: AsyncConnectionPool,
    conversation_id: uuid.UUID,
    user_id: uuid.UUID,
    title: str,
) -> Conversation | None:
    async with pool.connection() as connection, connection.cursor(
        row_factory=class_row(Conversation)
    ) as cursor:
        await cursor.execute(
            f"""UPDATE conversations SET title = %s, updated_at = NOW()
                WHERE id = %s AND user_id = %s RETURNING {FIELDS}""",
            (title, conversation_id, user_id),
        )
        return await cursor.fetchone()


async def touch(
    pool: AsyncConnectionPool,
    conversation_id: uuid.UUID,
    title: str | None = None,
) -> None:
    async with pool.connection() as connection:
        await connection.execute(
            """UPDATE conversations
               SET title = COALESCE(title, %s), updated_at = NOW()
               WHERE id = %s""",
            (title, conversation_id),
        )


async def delete(
    pool: AsyncConnectionPool,
    conversation_id: uuid.UUID,
    user_id: uuid.UUID,
) -> bool:
    async with pool.connection() as connection:
        cursor = await connection.execute(
            "DELETE FROM conversations WHERE id = %s AND user_id = %s",
            (conversation_id, user_id),
        )
        return cursor.rowcount == 1
