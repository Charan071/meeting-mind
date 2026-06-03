"""Formatters for Slack blocks and HTML email digests."""
from __future__ import annotations

from app.models.action_item import ActionItem
from app.models.meeting import Meeting, MeetingExtraction

PRIORITY_EMOJI = {
    "critical": "🔴",
    "high": "🟠",
    "medium": "🔵",
    "low": "⚪",
}


# ---------------------------------------------------------------------------
# Slack
# ---------------------------------------------------------------------------

def build_slack_blocks(
    meeting: Meeting,
    extraction: MeetingExtraction,
    action_items: list[ActionItem],
) -> list[dict]:
    import json

    decisions = json.loads(extraction.decisions)
    open_questions = json.loads(extraction.open_questions)

    blocks: list[dict] = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"📋 {meeting.title}", "emoji": True},
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Summary*\n{extraction.summary}"},
        },
    ]

    if action_items:
        blocks.append({"type": "divider"})
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Action Items ({len(action_items)})*"},
        })
        for item in action_items:
            emoji = PRIORITY_EMOJI.get(item.priority, "🔵")
            owner_str = f" — _{item.owner_name}_" if item.owner_name else ""
            deadline_str = f" · due {item.deadline.strftime('%b %d')}" if item.deadline else ""
            quote_str = f"\n> _{item.verbatim_quote}_" if item.verbatim_quote else ""
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{emoji} {item.task}{owner_str}{deadline_str}{quote_str}",
                },
            })

    if decisions:
        blocks.append({"type": "divider"})
        decision_text = "\n".join(f"✅ {d}" for d in decisions)
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Decisions*\n{decision_text}"},
        })

    if open_questions:
        q_text = "\n".join(f"❓ {q}" for q in open_questions)
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Open Questions*\n{q_text}"},
        })

    blocks.append({"type": "divider"})
    blocks.append({
        "type": "context",
        "elements": [{"type": "mrkdwn", "text": "Powered by *MeetingMind* · _Every commitment, tracked._"}],
    })

    return blocks


def build_slack_text(meeting: Meeting, extraction: MeetingExtraction) -> str:
    return f"Meeting digest: *{meeting.title}* — {extraction.summary[:120]}…"


# ---------------------------------------------------------------------------
# Email (HTML)
# ---------------------------------------------------------------------------

def build_email_html(
    meeting: Meeting,
    extraction: MeetingExtraction,
    action_items: list[ActionItem],
) -> str:
    import json

    decisions = json.loads(extraction.decisions)
    open_questions = json.loads(extraction.open_questions)

    def _ai_rows(items: list[ActionItem]) -> str:
        rows = []
        for item in items:
            emoji = PRIORITY_EMOJI.get(item.priority, "🔵")
            owner = f"<span style='color:#5C5C5C'>— {item.owner_name}</span>" if item.owner_name else ""
            deadline = f"<span style='color:#5C5C5C'> · due {item.deadline.strftime('%b %d, %Y')}</span>" if item.deadline else ""
            quote = f"<blockquote style='border-left:3px solid #4F52B2;margin:4px 0 0 0;padding:2px 0 2px 10px;color:#5C5C5C;font-family:monospace;font-size:13px'>{item.verbatim_quote}</blockquote>" if item.verbatim_quote else ""
            rows.append(
                f"<tr><td style='padding:8px 0;border-bottom:1px solid #E8E8E8'>"
                f"{emoji} <strong>{item.task}</strong> {owner}{deadline}{quote}"
                f"</td></tr>"
            )
        return "".join(rows)

    def _list_items(items: list[str], emoji: str) -> str:
        return "".join(f"<li style='margin:4px 0'>{emoji} {i}</li>" for i in items)

    action_section = ""
    if action_items:
        action_section = f"""
        <h3 style='color:#4F52B2;font-size:14px;margin:24px 0 8px'>Action Items</h3>
        <table style='width:100%;border-collapse:collapse'>{_ai_rows(action_items)}</table>
        """

    decision_section = ""
    if decisions:
        decision_section = f"""
        <h3 style='color:#4F52B2;font-size:14px;margin:24px 0 8px'>Decisions</h3>
        <ul style='padding-left:16px;margin:0'>{_list_items(decisions, "✅")}</ul>
        """

    question_section = ""
    if open_questions:
        question_section = f"""
        <h3 style='color:#4F52B2;font-size:14px;margin:24px 0 8px'>Open Questions</h3>
        <ul style='padding-left:16px;margin:0'>{_list_items(open_questions, "❓")}</ul>
        """

    return f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style='font-family:Segoe UI,system-ui,sans-serif;max-width:600px;margin:0 auto;color:#1A1A1A'>
  <div style='background:#4F52B2;padding:20px 24px;border-radius:4px 4px 0 0'>
    <h1 style='color:#fff;font-size:18px;margin:0'>📋 {meeting.title}</h1>
    <p style='color:#D4D5EF;font-size:13px;margin:4px 0 0'>Meeting Digest · MeetingMind</p>
  </div>
  <div style='background:#fff;border:1px solid #E8E8E8;border-top:none;padding:24px;border-radius:0 0 4px 4px'>
    <h3 style='color:#4F52B2;font-size:14px;margin:0 0 8px'>Summary</h3>
    <p style='color:#333;line-height:1.6;margin:0'>{extraction.summary}</p>
    {action_section}
    {decision_section}
    {question_section}
    <hr style='border:none;border-top:1px solid #E8E8E8;margin:24px 0 16px'>
    <p style='font-size:12px;color:#838383;margin:0'>Powered by <strong>MeetingMind</strong> · Every commitment, tracked.</p>
  </div>
</body>
</html>
"""


def build_email_subject(meeting: Meeting) -> str:
    return f"[MeetingMind] {meeting.title} — meeting digest"
