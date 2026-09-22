from datetime import datetime, timezone
from typing import Annotated

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from chatbot.api.dependencies import get_current_user
from chatbot.db.models.user import User
from chatbot.repositories import users
from chatbot.schemas.auth import (
    Credentials,
    RefreshRequest,
    TokenPair,
    UserResponse,
)
from chatbot.security.password import hash_password, verify_password
from chatbot.security.tokens import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_user_id_from_token,
    hash_refresh_token,
)


router = APIRouter(prefix="/auth", tags=["Auth"])


async def issue_tokens(request: Request, user: User) -> TokenPair:
    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)
    expires_at = datetime.fromtimestamp(
        decode_token(refresh_token, "refresh")["exp"], timezone.utc
    )
    await users.store_refresh_token(
        request.app.state.db,
        hash_refresh_token(refresh_token),
        user.id,
        expires_at,
    )
    return TokenPair(access_token=access_token, refresh_token=refresh_token)


@router.post(
    "/register", response_model=TokenPair, status_code=status.HTTP_201_CREATED
)
async def register(body: Credentials, request: Request) -> TokenPair:
    user = await users.create_user(
        request.app.state.db, str(body.email), hash_password(body.password)
    )
    if user is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email is already registered")
    return await issue_tokens(request, user)


@router.post("/login", response_model=TokenPair)
async def login(body: Credentials, request: Request) -> TokenPair:
    user = await users.get_user_by_email(request.app.state.db, str(body.email))
    if (
        user is None
        or not user.is_active
        or not verify_password(body.password, user.password_hash)
    ):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Incorrect email or password"
        )
    return await issue_tokens(request, user)


@router.post("/refresh", response_model=TokenPair)
async def refresh(body: RefreshRequest, request: Request) -> TokenPair:
    unauthorized = HTTPException(
        status.HTTP_401_UNAUTHORIZED, "Invalid or expired refresh token"
    )
    try:
        user_id = get_user_id_from_token(body.refresh_token, "refresh")
    except jwt.InvalidTokenError:
        raise unauthorized
    if not await users.consume_refresh_token(
        request.app.state.db,
        hash_refresh_token(body.refresh_token),
        user_id,
    ):
        raise unauthorized
    user = await users.get_user(request.app.state.db, user_id)
    if user is None or not user.is_active:
        raise unauthorized
    return await issue_tokens(request, user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(body: RefreshRequest, request: Request) -> Response:
    await users.revoke_refresh_token(
        request.app.state.db, hash_refresh_token(body.refresh_token)
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=UserResponse)
async def me(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    return current_user
