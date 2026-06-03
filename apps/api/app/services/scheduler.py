"""Meeting bot scheduler — dispatches Recall.ai bots at the right time.

Uses Celery's eta parameter to enqueue a join task that fires at the
meeting's start_time (minus a small lead time so the bot is ready).
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.core.logging import logger

# How many seconds before the meeting starts the bot should join
BOT_LEAD_SECONDS = 60


def schedule_bot_join(meeting_id: str, start_time: datetime) -> str:
    """
    Schedule the auto_join_meeting Celery task to fire at start_time.
    Returns the Celery task ID.
    """
    from app.workers.tasks import auto_join_meeting

    # Ensure timezone-aware
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=UTC)

    eta = start_time - timedelta(seconds=BOT_LEAD_SECONDS)
    now = datetime.now(UTC)

    if eta <= now:
        # Meeting is already starting — join immediately
        eta = now + timedelta(seconds=5)

    result = auto_join_meeting.apply_async(args=[meeting_id], eta=eta)
    logger.info(
        "bot_join_scheduled",
        meeting_id=meeting_id,
        eta=eta.isoformat(),
        task_id=result.id,
    )
    return result.id


def cancel_scheduled_join(task_id: str) -> None:
    """Revoke a previously scheduled bot join (e.g. if event was deleted)."""
    from app.workers.celery_app import celery_app
    celery_app.control.revoke(task_id, terminate=False)
    logger.info("scheduled_join_cancelled", task_id=task_id)
