from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert

from chatbot.db.database import SessionFactory
from chatbot.db.models.memory import UserMemory


async def save(
    session_factory: SessionFactory, user_id: UUID, key: str, content: str
) -> None:
    key, content = key.strip(), content.strip()
    if not key or len(key) > 100:
        raise ValueError("Memory keys must contain between 1 and 100 characters.")
    if not content or len(content) > 4000:
        raise ValueError("Memory content must contain between 1 and 4,000 characters.")
    statement = insert(UserMemory).values(user_id=user_id, key=key, content=content)
    statement = statement.on_conflict_do_update(
        index_elements=[UserMemory.user_id, UserMemory.key],
        set_={"content": statement.excluded.content, "updated_at": func.now()},
    )
    async with session_factory() as session:
        await session.execute(statement)
        await session.commit()


async def list_for_user(
    session_factory: SessionFactory, user_id: UUID
) -> list[UserMemory]:
    async with session_factory() as session:
        result = await session.scalars(
            select(UserMemory)
            .where(UserMemory.user_id == user_id)
            .order_by(UserMemory.key)
        )
        return list(result)
