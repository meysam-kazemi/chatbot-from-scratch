import hashlib
import uuid
from datetime import datetime, timedelta, timezone

import jwt

from chatbot.config import settings


def create_access_token(
    user_id: uuid.UUID,
) -> str:
    now = datetime.now(timezone.utc)

    payload = {
        "sub": str(user_id),
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + timedelta(
            minutes=settings.access_token_expire_minutes
        ),
        "type": "access",
    }

    return jwt.encode(
        payload,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


def decode_token(token: str, expected_type: str) -> dict:
    payload = jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=[settings.jwt_algorithm],
        options={"require": ["sub", "jti", "iat", "exp", "type"]},
    )
    if payload["type"] != expected_type:
        raise jwt.InvalidTokenError(f"Expected {expected_type} token")
    try:
        uuid.UUID(payload["sub"])
    except (ValueError, TypeError) as exc:
        raise jwt.InvalidTokenError("Invalid subject") from exc
    return payload


def create_refresh_token(
    user_id: uuid.UUID,
) -> str:
    now = datetime.now(timezone.utc)

    payload = {
        "sub": str(user_id),
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + timedelta(
            days=settings.refresh_token_expire_days
        ),
        "type": "refresh",
    }

    return jwt.encode(
        payload,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


def get_user_id_from_token(token: str, token_type: str = "access") -> uuid.UUID:
    return uuid.UUID(decode_token(token, token_type)["sub"])


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
