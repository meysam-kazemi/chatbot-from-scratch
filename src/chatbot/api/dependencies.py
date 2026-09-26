from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from chatbot.ai.agent import AgenticChatbot
from chatbot.db.models.user import User
from chatbot.repositories.users import get_user
from chatbot.security.tokens import get_user_id_from_token


bearer = HTTPBearer(auto_error=False)


def get_chatbot(request: Request) -> AgenticChatbot:
    return request.app.state.chatbot


async def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized
    try:
        user_id = get_user_id_from_token(credentials.credentials)
    except jwt.InvalidTokenError:
        raise unauthorized
    user = await get_user(request.app.state.db, user_id)
    if user is None or not user.is_active:
        raise unauthorized
    return user
