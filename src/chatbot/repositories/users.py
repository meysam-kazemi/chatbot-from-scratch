import uuid
from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from chatbot.db.database import SessionFactory
from chatbot.db.models.user import RefreshToken, User


async def create_user(
    session_factory: SessionFactory,
    email: str,
    username: str,
    password_hash: str,
) -> User | None:
    user = User(
        id=uuid.uuid4(),
        email=email,
        username=username,
        password_hash=password_hash,
    )
    async with session_factory() as session:
        try:
            session.add(user)
            await session.commit()
            await session.refresh(user)
            return user
        except IntegrityError:
            await session.rollback()
            return None


async def get_user_by_email(
    session_factory: SessionFactory, email: str
) -> User | None:
    async with session_factory() as session:
        return await session.scalar(select(User).where(User.email == email))


async def get_user(
    session_factory: SessionFactory, user_id: uuid.UUID
) -> User | None:
    async with session_factory() as session:
        return await session.get(User, user_id)


async def store_refresh_token(
    session_factory: SessionFactory,
    token_hash: str,
    user_id: uuid.UUID,
    expires_at: datetime,
) -> None:
    async with session_factory() as session:
        session.add(
            RefreshToken(
                token_hash=token_hash,
                user_id=user_id,
                expires_at=expires_at,
            )
        )
        await session.commit()


async def consume_refresh_token(
    session_factory: SessionFactory, token_hash: str, user_id: uuid.UUID
) -> bool:
    async with session_factory() as session:
        result = await session.execute(
            delete(RefreshToken).where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.user_id == user_id,
                RefreshToken.expires_at > datetime.now(timezone.utc),
            )
        )
        await session.commit()
        return result.rowcount == 1


async def revoke_refresh_token(
    session_factory: SessionFactory, token_hash: str
) -> None:
    async with session_factory() as session:
        await session.execute(
            delete(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        await session.commit()
