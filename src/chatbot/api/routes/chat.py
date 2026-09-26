from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from langchain_core.messages import AIMessage

from chatbot.ai.agent import AgenticChatbot
from chatbot.api.dependencies import get_chatbot, get_current_user
from chatbot.db.models.user import User
from chatbot.repositories import conversations
from chatbot.schemas.chat import (
    ConversationCreate,
    ConversationHistory,
    ConversationResponse,
    ConversationUpdate,
    MessageResponse,
    SendMessageRequest,
)


router = APIRouter(prefix="/chat", tags=["Chat"])


async def owned_conversation(
    request: Request, conversation_id: UUID, user: User
):
    conversation = await conversations.get_for_user(
        request.app.state.db, conversation_id, user.id
    )
    if conversation is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")
    return conversation


@router.post(
    "/conversations",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_conversation(
    body: ConversationCreate,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
):
    return await conversations.create(request.app.state.db, user.id, body.title)


@router.get("/conversations", response_model=list[ConversationResponse])
async def list_conversations(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    return await conversations.list_for_user(
        request.app.state.db, user.id, limit, offset
    )


@router.patch(
    "/conversations/{conversation_id}", response_model=ConversationResponse
)
async def rename_conversation(
    conversation_id: UUID,
    body: ConversationUpdate,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
):
    conversation = await conversations.update(
        request.app.state.db, conversation_id, user.id, body.title
    )
    if conversation is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")
    return conversation


@router.delete(
    "/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_conversation(
    conversation_id: UUID,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    chatbot: Annotated[AgenticChatbot, Depends(get_chatbot)],
) -> Response:
    if not await conversations.delete(
        request.app.state.db, conversation_id, user.id
    ):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")
    await chatbot.adelete_conversation(str(conversation_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=ConversationHistory,
)
async def get_messages(
    conversation_id: UUID,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    chatbot: Annotated[AgenticChatbot, Depends(get_chatbot)],
) -> ConversationHistory:
    await owned_conversation(request, conversation_id, user)
    messages = await chatbot.aget_messages(str(conversation_id))
    return ConversationHistory(
        conversation_id=conversation_id,
        messages=[
            MessageResponse(
                role="assistant" if isinstance(message, AIMessage) else "user",
                content=str(message.content),
            )
            for message in messages
        ],
    )


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=MessageResponse,
)
async def send_message(
    conversation_id: UUID,
    body: SendMessageRequest,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    chatbot: Annotated[AgenticChatbot, Depends(get_chatbot)],
) -> MessageResponse:
    conversation = await owned_conversation(request, conversation_id, user)
    answer = await chatbot.ainvoke(
        body.message,
        str(conversation_id),
        context={
            "user_id": str(user.id),
            "conversation_id": str(conversation_id),
            "db": request.app.state.db,
        },
    )
    title = body.message[:100] if conversation.title is None else None
    await conversations.touch(request.app.state.db, conversation_id, title)
    return MessageResponse(role="assistant", content=answer)
