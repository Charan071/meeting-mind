"""Add scheduled_task_id to meetings for cancel support

Revision ID: 004
Revises: 003
Create Date: 2026-05-31
"""
from alembic import op
import sqlalchemy as sa

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Store the Celery task ID so we can cancel if event is deleted
    op.add_column("meetings", sa.Column("scheduled_task_id", sa.String(), nullable=True))

    # Index for the safety-net query (scheduled + has url + no bot + near start_time)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_meetings_scheduled_join
        ON meetings (started_at)
        WHERE status = 'scheduled'
          AND meeting_url IS NOT NULL
          AND recall_bot_id IS NULL
    """)

    # Index series lookups
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_meeting_series_owner
        ON meeting_series (owner_id, title)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_meetings_scheduled_join")
    op.execute("DROP INDEX IF EXISTS ix_meeting_series_owner")
    op.drop_column("meetings", "scheduled_task_id")
