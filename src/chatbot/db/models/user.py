from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CHAR,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    func,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column

from chatbot.db.models.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True)
    username: Mapped[str | None] = mapped_column(String(30))
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=true())
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


Index(
    "users_username_key",
    func.lower(User.username),
    unique=True,
    postgresql_where=User.username.is_not(None),
)


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    token_hash: Mapped[str] = mapped_column(CHAR(64), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


Index("refresh_tokens_user_id_idx", RefreshToken.user_id)
