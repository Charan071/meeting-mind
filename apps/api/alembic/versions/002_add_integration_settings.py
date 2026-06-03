"""add integration_settings table

Revision ID: 002
Revises: 001
Create Date: 2026-05-31
"""
from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # integration_settings already in 001 — this is a no-op placeholder
    # for future per-integration config columns (e.g. jira_project_key)
    op.add_column(
        "integration_settings",
        sa.Column("jira_project_key", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("integration_settings", "jira_project_key")
