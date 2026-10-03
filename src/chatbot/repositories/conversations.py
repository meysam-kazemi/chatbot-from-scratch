import uuid

from sqlalchemy import delete as sql_delete
from sqlalchemy import func, select, update as sql_update

from chatbot.db.database import SessionFactory
from chatbot.db.models.conversation import Conversation


async def create(
    session_factory: SessionFactory, user_id: uuid.UUID, title: str | None
) -> Conversation:
    conversation = Conversation(id=uuid.uuid4(), user_id=user_id, title=title)
    async with session_factory() as session:
        session.add(conversation)
        await session.commit()
        await session.refresh(conversation)
        return conversation


async def list_for_user(
    session_factory: SessionFactory,
    user_id: uuid.UUID,
    limit: int,
    offset: int,
) -> list[Conversation]:
    async with session_factory() as session:
        result = await session.scalars(
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(Conversation.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result)


async def get_for_user(
    session_factory: SessionFactory,
    conversation_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Conversation | None:
    async with session_factory() as session:
        return await session.scalar(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
            )
        )


async def update(
    session_factory: SessionFactory,
    conversation_id: uuid.UUID,
    user_id: uuid.UUID,
    title: str,
) -> Conversation | None:
    async with session_factory() as session:
        result = await session.scalars(
            sql_update(Conversation)
            .where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
            )
            .values(title=title, updated_at=func.now())
            .returning(Conversation)
        )
        conversation = result.one_or_none()
        await session.commit()
        return conversation


async def touch(
    session_factory: SessionFactory,
    conversation_id: uuid.UUID,
    title: str | None = None,
) -> None:
    async with session_factory() as session:
        await session.execute(
            sql_update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(
                title=func.coalesce(Conversation.title, title),
                updated_at=func.now(),
            )
        )
        await session.commit()


async def delete(
    session_factory: SessionFactory,
    conversation_id: uuid.UUID,
    user_id: uuid.UUID,
) -> bool:
    async with session_factory() as session:
        result = await session.execute(
            sql_delete(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
            )
        )
        await session.commit()
        return result.rowcount == 1
