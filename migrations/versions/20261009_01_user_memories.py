"""Add user-scoped long-term memory."""
from alembic import op
import sqlalchemy as sa

revision = "20261009_01"
down_revision = "eefc36dc0216"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_memories",
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("key", sa.String(100), primary_key=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("user_memories")
