import unittest

from chatbot.db.database import sqlalchemy_url
from chatbot.db.models import Base


class DatabaseTest(unittest.TestCase):
    def test_sqlalchemy_uses_psycopg_and_exposes_application_tables(self):
        self.assertEqual(
            sqlalchemy_url("postgresql+asyncpg://user:pass@db/chatbot"),
            "postgresql+psycopg://user:pass@db/chatbot",
        )
        self.assertEqual(
            set(Base.metadata.tables),
            {"users", "refresh_tokens", "conversations", "traces"},
        )


if __name__ == "__main__":
    unittest.main()
