"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-05-31
"""
from alembic import op
import sqlalchemy as sa

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "users",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("email", sa.String(), nullable=False, unique=True),
        sa.Column("name", sa.String()),
        sa.Column("image", sa.String()),
        sa.Column("google_id", sa.String(), unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_google_id", "users", ["google_id"])

    op.create_table(
        "meeting_series",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("owner_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "meetings",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("owner_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("series_id", sa.String(), sa.ForeignKey("meeting_series.id")),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="scheduled"),
        sa.Column("platform", sa.String()),
        sa.Column("meeting_url", sa.String()),
        sa.Column("recall_bot_id", sa.String(), unique=True),
        sa.Column("transcript_url", sa.String()),
        sa.Column("summary_short", sa.Text()),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("ended_at", sa.DateTime(timezone=True)),
        sa.Column("duration_seconds", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_meetings_owner_id", "meetings", ["owner_id"])
    op.create_index("ix_meetings_recall_bot_id", "meetings", ["recall_bot_id"])

    op.create_table(
        "participants",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("meeting_id", sa.String(), sa.ForeignKey("meetings.id"), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("email", sa.String()),
        sa.Column("speaker_label", sa.String()),
        sa.Column("joined_at", sa.DateTime(timezone=True)),
        sa.Column("left_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_participants_meeting_id", "participants", ["meeting_id"])

    op.create_table(
        "meeting_extractions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("meeting_id", sa.String(), sa.ForeignKey("meetings.id"), nullable=False, unique=True),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("decisions", sa.Text(), server_default="[]"),
        sa.Column("open_questions", sa.Text(), server_default="[]"),
        sa.Column("raw_transcript", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "action_items",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("meeting_id", sa.String(), sa.ForeignKey("meetings.id"), nullable=False),
        sa.Column("task", sa.Text(), nullable=False),
        sa.Column("owner_name", sa.String()),
        sa.Column("owner_email", sa.String()),
        sa.Column("deadline", sa.DateTime(timezone=True)),
        sa.Column("priority", sa.String(), nullable=False, server_default="medium"),
        sa.Column("status", sa.String(), nullable=False, server_default="open"),
        sa.Column("verbatim_quote", sa.Text()),
        sa.Column("resolved_in_meeting_id", sa.String(), sa.ForeignKey("meetings.id")),
        sa.Column("embedding_id", sa.String()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_action_items_meeting_id", "action_items", ["meeting_id"])
    op.create_index("ix_action_items_status", "action_items", ["status"])
    op.create_index("ix_action_items_owner_email", "action_items", ["owner_email"])

    op.create_table(
        "integrations",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="disconnected"),
        sa.Column("connected_at", sa.DateTime(timezone=True)),
        sa.Column("last_sync_at", sa.DateTime(timezone=True)),
        sa.Column("error_message", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_integrations_user_id", "integrations", ["user_id"])

    op.create_table(
        "integration_settings",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False, unique=True),
        sa.Column("slack_enabled", sa.Boolean(), server_default="false"),
        sa.Column("slack_channel_id", sa.String()),
        sa.Column("gmail_enabled", sa.Boolean(), server_default="false"),
        sa.Column("linear_enabled", sa.Boolean(), server_default="false"),
        sa.Column("jira_enabled", sa.Boolean(), server_default="false"),
        sa.Column("asana_enabled", sa.Boolean(), server_default="false"),
        sa.Column("hubspot_enabled", sa.Boolean(), server_default="false"),
        sa.Column("salesforce_enabled", sa.Boolean(), server_default="false"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("integration_settings")
    op.drop_table("integrations")
    op.drop_table("action_items")
    op.drop_table("meeting_extractions")
    op.drop_table("participants")
    op.drop_table("meetings")
    op.drop_table("meeting_series")
    op.drop_table("users")
