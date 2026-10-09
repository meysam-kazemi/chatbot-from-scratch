"""Consolidate keyed memories into one Markdown document per user."""
from alembic import op
import sqlalchemy as sa

revision = "20261009_02"
down_revision = "20261009_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_memory_documents",
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.execute(sa.text("""
        INSERT INTO user_memory_documents (user_id, content, updated_at)
        SELECT user_id,
               string_agg('## ' || key || E'\n\n' || content, E'\n\n' ORDER BY key),
               max(updated_at)
        FROM user_memories
        GROUP BY user_id
    """))
    op.drop_table("user_memories")
    op.rename_table("user_memory_documents", "user_memories")


def downgrade() -> None:
    # Preserve the complete document as one legacy entry; original keys cannot
    # be reconstructed after arbitrary edits to the Markdown document.
    op.add_column("user_memories", sa.Column("key", sa.String(100), server_default="document", nullable=False))
    op.drop_constraint("user_memory_documents_pkey", "user_memories", type_="primary")
    op.create_primary_key("user_memories_pkey", "user_memories", ["user_id", "key"])
    op.alter_column("user_memories", "key", server_default=None)
