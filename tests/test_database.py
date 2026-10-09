import unittest
import uuid
from types import SimpleNamespace

from sqlalchemy.dialects import postgresql

from chatbot.db.database import sqlalchemy_url
from chatbot.db.models import Base
from chatbot.repositories import conversations


class DatabaseTest(unittest.TestCase):
    def test_sqlalchemy_uses_psycopg_and_exposes_application_tables(self):
        self.assertEqual(
            sqlalchemy_url("postgresql+asyncpg://user:pass@db/chatbot"),
            "postgresql+psycopg://user:pass@db/chatbot",
        )
        self.assertEqual(
            set(Base.metadata.tables),
            {"users", "refresh_tokens", "conversations", "traces", "user_memories"},
        )


class _CapturingSession:
    def __init__(self, rowcount: int):
        self.rowcount = rowcount
        self.statement = None
        self.committed = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        return None

    async def execute(self, statement):
        self.statement = statement
        return SimpleNamespace(rowcount=self.rowcount)

    async def commit(self):
        self.committed = True


class ConversationRepositoryTest(unittest.IsolatedAsyncioTestCase):
    async def test_delete_only_matches_active_conversations(self):
        session = _CapturingSession(rowcount=0)

        deleted = await conversations.delete(
            lambda: session,
            uuid.uuid4(),
            uuid.uuid4(),
        )

        sql = str(
            session.statement.compile(
                dialect=postgresql.dialect(),
                compile_kwargs={"literal_binds": True},
            )
        )
        self.assertIn("conversations.is_active IS true", sql)
        self.assertFalse(deleted)
        self.assertTrue(session.committed)


if __name__ == "__main__":
    unittest.main()
