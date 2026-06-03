"""Slack slash command handler — /done [task-id]."""
from fastapi import APIRouter, Form, HTTPException, Request
from sqlalchemy import select

from app.core.logging import logger
from app.db.base import AsyncSessionLocal
from app.models.action_item import ActionItem
from app.services.state_machine import InvalidTransitionError, validate_transition

router = APIRouter(prefix="/slack", tags=["slack"])


@router.post("/commands")
async def slack_command(
    request: Request,
    command: str = Form(...),
    text: str = Form(default=""),
    user_name: str = Form(default=""),
    user_id: str = Form(default=""),
):
    """
    Handle /done [item-id] and /defer [item-id] slash commands from Slack.
    Slack sends these as application/x-www-form-urlencoded.
    """
    log = logger.bind(command=command, user=user_name, text=text)
    log.info("slack_command_received")

    parts = text.strip().split()
    if not parts:
        return _ephemeral("Usage: `/done <task-id>` or `/defer <task-id>`")

    action = command.lstrip("/").lower()  # "done" or "defer"
    item_id = parts[0]

    target_status = {"done": "done", "defer": "deferred"}.get(action)
    if not target_status:
        return _ephemeral(f"Unknown command: {command}")

    async with AsyncSessionLocal() as db:
        item = await db.get(ActionItem, item_id)
        if not item:
            return _ephemeral(f"Task `{item_id}` not found.")

        try:
            validate_transition(item.status, target_status)
        except InvalidTransitionError as e:
            return _ephemeral(str(e))

        item.status = target_status
        await db.commit()
        await db.refresh(item)

    emoji = "✅" if target_status == "done" else "⏸️"
    verb = "marked as done" if target_status == "done" else "deferred"
    log.info("slack_command_applied", item_id=item_id, status=target_status)

    return {
        "response_type": "ephemeral",
        "text": f"{emoji} *{item.task}* has been {verb}.",
    }


def _ephemeral(text: str) -> dict:
    return {"response_type": "ephemeral", "text": text}
