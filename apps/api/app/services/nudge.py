"""Overdue nudge service — sends Slack DMs to action item owners."""
from __future__ import annotations

from datetime import UTC, datetime

from app.core.logging import logger
from app.models.action_item import ActionItem
from app.models.meeting import Meeting
from app.services.composio import composio


def _build_nudge_text(item: ActionItem, meeting: Meeting) -> str:
    days_overdue = (datetime.now(UTC) - item.deadline.replace(tzinfo=UTC)).days if item.deadline else 0
    overdue_str = f" ({days_overdue}d overdue)" if days_overdue > 0 else ""

    lines = [
        f"👋 *Reminder: you have an overdue commitment{overdue_str}*",
        "",
        f"*Task:* {item.task}",
        f"*From meeting:* {meeting.title}",
    ]
    if item.deadline:
        lines.append(f"*Was due:* {item.deadline.strftime('%b %d, %Y')}")
    if item.verbatim_quote:
        lines.append(f"\n> _{item.verbatim_quote}_")
    lines.append("\nReply `/done {item_id}` in Slack to mark this complete, or update it in MeetingMind.")
    return "\n".join(lines)


def _build_nudge_blocks(item: ActionItem, meeting: Meeting) -> list[dict]:
    days_overdue = (datetime.now(UTC) - item.deadline.replace(tzinfo=UTC)).days if item.deadline else 0

    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"👋 *Overdue commitment{f' — {days_overdue}d late' if days_overdue else ''}*",
            },
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Task*\n{item.task}"},
                {"type": "mrkdwn", "text": f"*From*\n{meeting.title}"},
                *([{"type": "mrkdwn", "text": f"*Was due*\n{item.deadline.strftime('%b %d, %Y')}"}] if item.deadline else []),
            ],
        },
    ]

    if item.verbatim_quote:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Original quote*\n> _{item.verbatim_quote}_",
            },
        })

    blocks.append({
        "type": "actions",
        "elements": [
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "Mark Done"},
                "style": "primary",
                "action_id": "mark_done",
                "value": item.id,
            },
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "Defer"},
                "action_id": "defer_item",
                "value": item.id,
            },
        ],
    })

    return blocks


async def send_nudge_dm(owner_id: str, item: ActionItem, meeting: Meeting) -> bool:
    """
    Send a Slack DM to the action item owner via Composio.
    Returns True on success, False on failure.
    """
    log = logger.bind(item_id=item.id, owner=item.owner_email)
    try:
        text = _build_nudge_text(item, meeting)
        blocks = _build_nudge_blocks(item, meeting)

        # DM the owner directly by their email (Composio resolves to Slack user)
        recipient = item.owner_email or item.owner_name or "unknown"
        await composio.send_slack_message(
            entity_id=owner_id,
            channel=f"@{recipient}",  # Slack DM syntax
            text=text,
            blocks=blocks,
        )
        log.info("nudge_dm_sent", recipient=recipient)
        return True
    except Exception as e:
        log.error("nudge_dm_failed", error=str(e))
        return False
