"""Post-extraction integration dispatcher.

Checks which integrations the meeting owner has enabled and fires them
in parallel. Each integration failure is logged but never blocks others.
"""
from __future__ import annotations

import asyncio
import json

from app.core.logging import logger
from app.models.action_item import ActionItem
from app.models.integration import IntegrationSettings
from app.models.meeting import Meeting, MeetingExtraction
from app.services.composio import composio
from app.services.digest import (
    build_email_html,
    build_email_subject,
    build_slack_blocks,
    build_slack_text,
)

PRIORITY_TO_LINEAR = {"critical": 1, "high": 2, "medium": 3, "low": 4}
PRIORITY_TO_JIRA = {"critical": "Highest", "high": "High", "medium": "Medium", "low": "Low"}


async def fire_integrations(
    owner_id: str,
    meeting: Meeting,
    extraction: MeetingExtraction,
    action_items: list[ActionItem],
    settings_row: IntegrationSettings | None,
    participant_emails: list[str],
) -> None:
    """Fan-out all enabled integrations. Errors are swallowed per-integration."""
    if not settings_row:
        logger.info("no_integration_settings", owner_id=owner_id)
        return

    tasks = []

    if settings_row.slack_enabled and settings_row.slack_channel_id:
        tasks.append(_safe("slack", _send_slack(owner_id, meeting, extraction, action_items, settings_row.slack_channel_id)))

    if settings_row.gmail_enabled and participant_emails:
        tasks.append(_safe("gmail", _send_gmail(owner_id, meeting, extraction, action_items, participant_emails)))

    if settings_row.linear_enabled:
        tasks.append(_safe("linear", _create_linear_issues(owner_id, meeting, action_items)))

    if settings_row.jira_enabled:
        tasks.append(_safe("jira", _create_jira_issues(owner_id, meeting, action_items)))

    if settings_row.hubspot_enabled:
        tasks.append(_safe("hubspot", _create_hubspot_note(owner_id, meeting, extraction, action_items)))

    if settings_row.salesforce_enabled:
        tasks.append(_safe("salesforce", _create_salesforce_tasks(owner_id, meeting, action_items)))

    if tasks:
        await asyncio.gather(*tasks)
        logger.info("integrations_fired", owner_id=owner_id, count=len(tasks))


async def _safe(name: str, coro) -> None:
    try:
        await coro
    except Exception as e:
        logger.error("integration_failed", integration=name, error=str(e))


# ---------------------------------------------------------------------------
# Individual integration handlers
# ---------------------------------------------------------------------------

async def _send_slack(
    owner_id: str,
    meeting: Meeting,
    extraction: MeetingExtraction,
    action_items: list[ActionItem],
    channel: str,
) -> None:
    blocks = build_slack_blocks(meeting, extraction, action_items)
    text = build_slack_text(meeting, extraction)
    await composio.send_slack_message(entity_id=owner_id, channel=channel, text=text, blocks=blocks)
    logger.info("slack_digest_sent", meeting_id=meeting.id, channel=channel)


async def _send_gmail(
    owner_id: str,
    meeting: Meeting,
    extraction: MeetingExtraction,
    action_items: list[ActionItem],
    recipients: list[str],
) -> None:
    html = build_email_html(meeting, extraction, action_items)
    subject = build_email_subject(meeting)
    await composio.send_email(entity_id=owner_id, to=recipients, subject=subject, body_html=html)
    logger.info("gmail_digest_sent", meeting_id=meeting.id, recipients=len(recipients))


async def _create_linear_issues(
    owner_id: str,
    meeting: Meeting,
    action_items: list[ActionItem],
) -> None:
    for item in action_items:
        priority = PRIORITY_TO_LINEAR.get(item.priority, 3)
        description = f"From meeting: **{meeting.title}**\n\n"
        if item.verbatim_quote:
            description += f"> {item.verbatim_quote}\n\n"
        if item.owner_name:
            description += f"Owner: {item.owner_name}\n"

        await composio.create_linear_issue(
            entity_id=owner_id,
            title=item.task,
            description=description,
            priority=priority,
        )
    logger.info("linear_issues_created", meeting_id=meeting.id, count=len(action_items))


async def _create_jira_issues(
    owner_id: str,
    meeting: Meeting,
    action_items: list[ActionItem],
) -> None:
    for item in action_items:
        priority = PRIORITY_TO_JIRA.get(item.priority, "Medium")
        description = f"From meeting: *{meeting.title}*\n\n"
        if item.verbatim_quote:
            description += f"bq. {item.verbatim_quote}\n\n"
        if item.owner_name:
            description += f"Owner: {item.owner_name}\n"

        # Jira project key stored in user settings (future: per-integration config)
        await composio.create_jira_issue(
            entity_id=owner_id,
            project_key="MM",  # TODO: make configurable per user
            summary=item.task,
            description=description,
            priority=priority,
        )
    logger.info("jira_issues_created", meeting_id=meeting.id, count=len(action_items))


async def _create_hubspot_note(
    owner_id: str,
    meeting: Meeting,
    extraction: MeetingExtraction,
    action_items: list[ActionItem],
) -> None:
    lines = [f"Meeting: {meeting.title}", "", extraction.summary, ""]
    if action_items:
        lines.append("Action Items:")
        for item in action_items:
            owner_str = f" ({item.owner_name})" if item.owner_name else ""
            lines.append(f"  • {item.task}{owner_str}")

    body = "\n".join(lines)
    await composio.create_hubspot_note(entity_id=owner_id, body=body)
    logger.info("hubspot_note_created", meeting_id=meeting.id)


async def _create_salesforce_tasks(
    owner_id: str,
    meeting: Meeting,
    action_items: list[ActionItem],
) -> None:
    for item in action_items:
        description = f"From meeting: {meeting.title}\n"
        if item.verbatim_quote:
            description += f"\n\"{item.verbatim_quote}\""

        await composio.create_salesforce_task(
            entity_id=owner_id,
            subject=item.task,
            description=description,
        )
    logger.info("salesforce_tasks_created", meeting_id=meeting.id, count=len(action_items))
