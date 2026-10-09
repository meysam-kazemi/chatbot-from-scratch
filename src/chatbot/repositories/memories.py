from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert

from chatbot.db.database import SessionFactory
from chatbot.db.models.memory import UserMemory


MAX_DOCUMENT_LENGTH = 50_000


async def save(
    session_factory: SessionFactory, user_id: UUID, content: str
) -> None:
    """Replace the user's entire Markdown memory document."""
    if len(content) > MAX_DOCUMENT_LENGTH:
        raise ValueError("Memory document exceeds the 50,000 character limit.")
    statement = insert(UserMemory).values(user_id=user_id, content=content)
    statement = statement.on_conflict_do_update(
        index_elements=[UserMemory.user_id],
        set_={"content": statement.excluded.content, "updated_at": func.now()},
    )
    async with session_factory() as session:
        await session.execute(statement)
        await session.commit()


async def get_for_user(session_factory: SessionFactory, user_id: UUID) -> str:
    """Read the complete document; users without memory start with empty text."""
    async with session_factory() as session:
        return await session.scalar(
            select(UserMemory.content).where(UserMemory.user_id == user_id)
        ) or ""
