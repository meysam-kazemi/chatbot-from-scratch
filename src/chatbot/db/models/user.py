

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class User:
    id: UUID
    email: str
    username: str | None
    password_hash: str
    is_active: bool
    created_at: datetime
