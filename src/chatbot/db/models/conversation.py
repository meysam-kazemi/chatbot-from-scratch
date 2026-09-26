from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class Conversation:
    id: UUID
    user_id: UUID
    title: str | None
    created_at: datetime
    updated_at: datetime
