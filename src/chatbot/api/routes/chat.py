import json
import logging

import anyio

from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse as FileDownloadResponse, StreamingResponse
from langchain_core.messages import AIMessage

from chatbot.ai.agent import AgenticChatbot
from chatbot.ai.title import TitleGenerator
from chatbot.ai.tracing import PostgresTracer
from chatbot.api.dependencies import get_chatbot, get_current_user, get_title_generator
from chatbot.db.models.user import User
from chatbot.repositories import conversations, files
from chatbot.schemas.chat import (
    ConversationCreate,
    ConversationHistory,
    ConversationResponse,
    ConversationUpdate,
    FileResponse,
    MessageResponse,
    SendMessageRequest,
)


logger = logging.getLogger(__name__)

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
    root = files.workspace(user.id, conversation_id)
    try:
        await chatbot.adelete_conversation(str(conversation_id))
    finally:
        files.delete_workspace(root)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/conversations/{conversation_id}/files",
    response_model=list[FileResponse],
)
async def list_conversation_files(
    conversation_id: UUID,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
):
    await owned_conversation(request, conversation_id, user)
    return files.list_files(files.workspace(user.id, conversation_id))


@router.post(
    "/conversations/{conversation_id}/files",
    response_model=FileResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_conversation_file(
    conversation_id: UUID,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    file: Annotated[UploadFile, File()],
):
    await owned_conversation(request, conversation_id, user)
    try:
        return await files.save_upload(
            files.workspace(user.id, conversation_id), file
        )
    except FileExistsError:
        raise HTTPException(status.HTTP_409_CONFLICT, "File already exists")
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))


@router.get("/conversations/{conversation_id}/files/{file_path:path}")
async def get_conversation_file(
    conversation_id: UUID,
    file_path: str,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
):
    await owned_conversation(request, conversation_id, user)
    try:
        root = files.workspace(user.id, conversation_id)
        path = files.safe_path(root, file_path)
    except ValueError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "File not found")
    if not path.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "File not found")
    info = files.describe(path, root)
    media_type = info["content_type"]
    headers = {"X-Content-Type-Options": "nosniff"}
    if media_type.startswith("text/"):
        return FileDownloadResponse(
            path, media_type="text/plain", headers=headers
        )
    if media_type in {"image/gif", "image/jpeg", "image/png", "image/webp"}:
        return FileDownloadResponse(path, media_type=media_type, headers=headers)
    return FileDownloadResponse(
        path, filename=path.name, media_type=media_type, headers=headers
    )


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
    title_generator: Annotated[TitleGenerator, Depends(get_title_generator)],
) -> MessageResponse:
    conversation = await owned_conversation(request, conversation_id, user)
    tracer = PostgresTracer(request.app.state.db, user.id, conversation_id)
    try:
        answer = await chatbot.ainvoke(
            body.message,
            str(conversation_id),
            context={
                "user_id": str(user.id),
                "conversation_id": str(conversation_id),
                "db": request.app.state.db,
            },
            callbacks=[tracer],
        )
        title = (
            await title_generator.ainvoke(body.message, callbacks=[tracer])
            if conversation.title is None
            else None
        )
    finally:
        await tracer.persist()
    await conversations.touch(request.app.state.db, conversation_id, title)
    return MessageResponse(role="assistant", content=answer)


@router.post("/conversations/{conversation_id}/messages/stream")
async def stream_message(
    conversation_id: UUID,
    body: SendMessageRequest,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    chatbot: Annotated[AgenticChatbot, Depends(get_chatbot)],
    title_generator: Annotated[TitleGenerator, Depends(get_title_generator)],
) -> StreamingResponse:
    conversation = await owned_conversation(request, conversation_id, user)

    def encode(event):
        return f"event: {event['event']}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"

    async def events():
        tracer = PostgresTracer(request.app.state.db, user.id, conversation_id)
        try:
            async for event in chatbot.astream(
                body.message, str(conversation_id),
                context={
                    "user_id": str(user.id),
                    "conversation_id": str(conversation_id),
                    "db": request.app.state.db,
                },
                callbacks=[tracer],
            ):
                yield encode(event)
            title = None
            if conversation.title is None:
                try:
                    title = await title_generator.ainvoke(body.message, callbacks=[tracer])
                except Exception:
                    logger.exception("stream_title_generation_failed")
            await conversations.touch(request.app.state.db, conversation_id, title)
            yield encode({"event": "done", "title": title})
        except Exception:
            logger.exception("chat_stream_failed conversation_id=%s", conversation_id)
            yield encode({"event": "error", "message": "The response was interrupted. Please reload the conversation before retrying."})
        finally:
            with anyio.move_on_after(5, shield=True):
                await tracer.persist()

    return StreamingResponse(
        events(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
