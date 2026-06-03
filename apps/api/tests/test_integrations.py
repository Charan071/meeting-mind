"""Tests for integration dispatcher and digest formatters."""
from unittest.mock import AsyncMock, MagicMock, patch
import json
import pytest

from app.models.action_item import ActionItem
from app.models.integration import IntegrationSettings
from app.models.meeting import Meeting, MeetingExtraction
from app.services.digest import (
    build_email_html,
    build_email_subject,
    build_slack_blocks,
    build_slack_text,
)


def _meeting() -> Meeting:
    m = MagicMock(spec=Meeting)
    m.id = "meet-1"
    m.title = "Q3 Planning"
    m.owner_id = "user-1"
    return m


def _extraction() -> MeetingExtraction:
    e = MagicMock(spec=MeetingExtraction)
    e.summary = "The team aligned on Q3 priorities. Budget was approved. Bob owns the roadmap."
    e.decisions = json.dumps(["Approve $200K mobile budget"])
    e.open_questions = json.dumps(["Who leads marketing?"])
    return e


def _action_items() -> list[ActionItem]:
    ai = MagicMock(spec=ActionItem)
    ai.task = "Write mobile roadmap"
    ai.owner_name = "Bob"
    ai.owner_email = "bob@example.com"
    ai.priority = "high"
    ai.verbatim_quote = "Bob, can you own the roadmap by Friday?"
    ai.deadline = None
    ai.status = "open"
    return [ai]


# --- Digest formatters ---

def test_slack_blocks_structure():
    blocks = build_slack_blocks(_meeting(), _extraction(), _action_items())
    types = [b["type"] for b in blocks]
    assert "header" in types
    assert "section" in types
    # Should contain the action item task
    texts = [b.get("text", {}).get("text", "") for b in blocks]
    assert any("mobile roadmap" in t for t in texts)


def test_slack_text():
    text = build_slack_text(_meeting(), _extraction())
    assert "Q3 Planning" in text


def test_email_html_contains_key_content():
    html = build_email_html(_meeting(), _extraction(), _action_items())
    assert "Q3 Planning" in html
    assert "mobile roadmap" in html
    assert "Bob" in html
    assert "Approve $200K" in html
    assert "Who leads marketing" in html


def test_email_subject():
    subject = build_email_subject(_meeting())
    assert "Q3 Planning" in subject
    assert "MeetingMind" in subject


# --- Integration dispatcher ---

@pytest.mark.asyncio
async def test_fire_integrations_slack_only():
    settings_row = MagicMock(spec=IntegrationSettings)
    settings_row.slack_enabled = True
    settings_row.slack_channel_id = "C012AB3CD"
    settings_row.gmail_enabled = False
    settings_row.linear_enabled = False
    settings_row.jira_enabled = False
    settings_row.hubspot_enabled = False
    settings_row.salesforce_enabled = False

    with patch("app.services.integrations.composio") as mock_composio:
        mock_composio.send_slack_message = AsyncMock(return_value={"ok": True})

        from app.services.integrations import fire_integrations
        await fire_integrations(
            owner_id="user-1",
            meeting=_meeting(),
            extraction=_extraction(),
            action_items=_action_items(),
            settings_row=settings_row,
            participant_emails=[],
        )

        mock_composio.send_slack_message.assert_awaited_once()
        call_kwargs = mock_composio.send_slack_message.call_args.kwargs
        assert call_kwargs["channel"] == "C012AB3CD"


@pytest.mark.asyncio
async def test_fire_integrations_no_settings():
    """With no settings row, nothing should blow up."""
    from app.services.integrations import fire_integrations
    await fire_integrations(
        owner_id="user-1",
        meeting=_meeting(),
        extraction=_extraction(),
        action_items=_action_items(),
        settings_row=None,
        participant_emails=[],
    )


@pytest.mark.asyncio
async def test_integration_failure_is_isolated():
    """A failing integration should not prevent others from running."""
    settings_row = MagicMock(spec=IntegrationSettings)
    settings_row.slack_enabled = True
    settings_row.slack_channel_id = "C123"
    settings_row.gmail_enabled = True
    settings_row.linear_enabled = False
    settings_row.jira_enabled = False
    settings_row.hubspot_enabled = False
    settings_row.salesforce_enabled = False

    with patch("app.services.integrations.composio") as mock_composio:
        mock_composio.send_slack_message = AsyncMock(side_effect=Exception("Slack down"))
        mock_composio.send_email = AsyncMock(return_value={"ok": True})

        from app.services.integrations import fire_integrations
        # Should not raise
        await fire_integrations(
            owner_id="user-1",
            meeting=_meeting(),
            extraction=_extraction(),
            action_items=_action_items(),
            settings_row=settings_row,
            participant_emails=["alice@example.com"],
        )

        # Gmail should still have fired despite Slack failing
        mock_composio.send_email.assert_awaited_once()
