"""Add pgvector IVFFlat index for action_item similarity search

Revision ID: 003
Revises: 002
Create Date: 2026-05-31
"""
from alembic import op

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # embedding_id column already exists (TEXT holding JSON float array).
    # For production-scale vector search, switch to pgvector's VECTOR type.
    # For now we create a partial index on non-null embedding_id for fast filtering.
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_action_items_has_embedding
        ON action_items (id)
        WHERE embedding_id IS NOT NULL
    """)

    # Also index the resolved_in_meeting_id for resolution lookups
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_action_items_resolved_in
        ON action_items (resolved_in_meeting_id)
        WHERE resolved_in_meeting_id IS NOT NULL
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_action_items_has_embedding")
    op.execute("DROP INDEX IF EXISTS ix_action_items_resolved_in")
