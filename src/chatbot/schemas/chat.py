from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ConversationCreate(BaseModel):
    title: str | None = Field(default=None, max_length=100)

    @field_validator("title")
    @classmethod
    def clean_title(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None


class ConversationUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=100)

    @field_validator("title")
    @classmethod
    def clean_title(cls, value: str) -> str:
        if not (value := value.strip()):
            raise ValueError("title cannot be empty")
        return value


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str | None
    created_at: datetime
    updated_at: datetime


class SendMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=20_000)

    @field_validator("message")
    @classmethod
    def clean_message(cls, value: str) -> str:
        if not (value := value.strip()):
            raise ValueError("message cannot be empty")
        return value


class MessageResponse(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ConversationHistory(BaseModel):
    conversation_id: UUID
    messages: list[MessageResponse]
