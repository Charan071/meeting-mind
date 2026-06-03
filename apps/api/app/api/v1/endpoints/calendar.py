"""Calendar webhook + management endpoints.

Composio delivers Google Calendar events here as they are created/updated.
We parse the event, create (or update) a Meeting row, then schedule the
Recall.ai bot to auto-join at the right time.
"""
from __future__ import annotations

import hashlib
import hmac

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger
from app.db.base import get_db
from app.models.meeting import Meeting, MeetingExtraction, MeetingSeries, Participant
from app.services.calendar import ParsedEvent, parse_calendar_event
from app.services.scheduler import cancel_scheduled_join, schedule_bot_join

router = APIRouter(prefix="/calendar", tags=["calendar"])


# ---------------------------------------------------------------------------
# Composio webhook — fires on Google Calendar event create/update/delete
# ---------------------------------------------------------------------------

@router.post("/webhook", status_code=status.HTTP_200_OK)
async def calendar_webhook(request: Request, background: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    body = await request.body()

    # Optional signature verification (Composio supports webhook secrets)
    if settings.COMPOSIO_API_KEY:
        sig = request.headers.get("x-composio-signature", "")
        expected = "sha256=" + hmac.new(
            settings.COMPOSIO_API_KEY.encode(), body, hashlib.sha256
        ).hexdigest()
        if sig and not hmac.compare_digest(expected, sig):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")

    payload = await request.json()
    event_type: str = payload.get("trigger", {}).get("type", "")
    entity_id: str = payload.get("entityId", "placeholder")
    raw_event: dict = payload.get("payload", {})

    log = logger.bind(event_type=event_type, entity_id=entity_id)
    log.info("calendar_webhook_received")

    if event_type in ("google_calendar_event_created", "google_calendar_event_updated"):
        background.add_task(_handle_event_upsert, raw_event, entity_id, db)

    elif event_type == "google_calendar_event_deleted":
        event_id = raw_event.get("id", "")
        background.add_task(_handle_event_deleted, event_id, db)

    return {"status": "ok"}


async def _handle_event_upsert(raw_event: dict, owner_id: str, db: AsyncSession) -> None:
    """Parse calendar event, upsert Meeting row, schedule bot join."""
    try:
        parsed = parse_calendar_event(raw_event)
    except Exception as e:
        logger.error("calendar_parse_failed", error=str(e))
        return

    if not parsed.meeting_url:
        logger.info("calendar_event_no_url", event_id=parsed.event_id)
        return

    log = logger.bind(event_id=parsed.event_id, title=parsed.title, platform=parsed.platform)
    log.info("calendar_event_processing")

    # Resolve or create MeetingSeries for recurring events
    series_id: str | None = None
    if parsed.is_recurring and parsed.recurrence_id:
        series_id = await _get_or_create_series(db, owner_id, parsed)

    # Upsert the Meeting row (idempotent on calendar event_id stored in meeting_url)
    existing_result = await db.execute(
        select(Meeting).where(
            Meeting.owner_id == owner_id,
            Meeting.meeting_url == parsed.meeting_url,
        )
    )
    meeting = existing_result.scalar_one_or_none()

    if meeting:
        # Update title/time if event was edited
        meeting.title = parsed.title
        meeting.started_at = parsed.start_time
        meeting.series_id = series_id or meeting.series_id
        await db.commit()
        log.info("calendar_meeting_updated", meeting_id=meeting.id)
    else:
        meeting = Meeting(
            owner_id=owner_id,
            title=parsed.title,
            status="scheduled",
            platform=parsed.platform,
            meeting_url=parsed.meeting_url,
            started_at=parsed.start_time,
            series_id=series_id,
        )
        db.add(meeting)
        await db.commit()
        await db.refresh(meeting)
        log.info("calendar_meeting_created", meeting_id=meeting.id)

        # Persist attendees
        for email in parsed.attendee_emails:
            db.add(Participant(meeting_id=meeting.id, name=email.split("@")[0], email=email))
        if parsed.organizer_email and parsed.organizer_email not in parsed.attendee_emails:
            db.add(Participant(
                meeting_id=meeting.id,
                name=parsed.organizer_email.split("@")[0],
                email=parsed.organizer_email,
            ))
        await db.commit()

    # Schedule the Recall.ai bot to join at start_time
    task_id = schedule_bot_join(meeting.id, parsed.start_time)

    # Persist the task ID so we can cancel if the event is later deleted
    async with AsyncSessionLocal() as db2:
        m = await db2.get(Meeting, meeting.id)
        if m:
            m.scheduled_task_id = task_id
            await db2.commit()

    # Notify owner via Slack that bot is scheduled
    await _notify_bot_scheduled(owner_id, meeting, parsed)


async def _handle_event_deleted(event_id: str, db: AsyncSession) -> None:
    logger.info("calendar_event_deleted", event_id=event_id)
    # Find the meeting by scheduled_task_id link (best-effort; no hard event_id column)
    # In practice, cancel all scheduled meetings whose URL matches — handled via task revoke
    from sqlalchemy import select as sa_select
    result = await db.execute(
        sa_select(Meeting).where(
            Meeting.status == "scheduled",
            Meeting.scheduled_task_id.isnot(None),
        )
    )
    for meeting in result.scalars().all():
        try:
            cancel_scheduled_join(meeting.scheduled_task_id)
            meeting.status = "cancelled"
            logger.info("scheduled_meeting_cancelled", meeting_id=meeting.id)
        except Exception as e:
            logger.warning("cancel_failed", meeting_id=meeting.id, error=str(e))
    await db.commit()


async def _get_or_create_series(
    db: AsyncSession, owner_id: str, parsed: ParsedEvent
) -> str:
    result = await db.execute(
        select(MeetingSeries).where(
            MeetingSeries.owner_id == owner_id,
            MeetingSeries.title == parsed.title,
        )
    )
    series = result.scalar_one_or_none()
    if not series:
        series = MeetingSeries(owner_id=owner_id, title=parsed.title)
        db.add(series)
        await db.commit()
        await db.refresh(series)
        logger.info("series_created", series_id=series.id, title=series.title)
    return series.id


async def _notify_bot_scheduled(owner_id: str, meeting: Meeting, parsed: ParsedEvent) -> None:
    from app.services.composio import composio
    from app.models.integration import IntegrationSettings
    from sqlalchemy import select
    from app.db.base import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(IntegrationSettings).where(IntegrationSettings.user_id == owner_id)
        )
        row = result.scalar_one_or_none()
        if not row or not row.slack_enabled or not row.slack_channel_id:
            return

    try:
        time_str = parsed.start_time.strftime("%b %d at %I:%M %p UTC")
        await composio.send_slack_message(
            entity_id=owner_id,
            channel=row.slack_channel_id,
            text=f"🤖 MeetingMind bot scheduled to join *{meeting.title}* on {time_str}.",
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            f"🤖 *Bot joining soon*\n"
                            f"*{meeting.title}*\n"
                            f"{time_str}\n"
                            f"Platform: {parsed.platform or 'unknown'}"
                        ),
                    },
                }
            ],
        )
    except Exception as e:
        logger.warning("bot_scheduled_notify_failed", error=str(e))


# ---------------------------------------------------------------------------
# Manual calendar management
# ---------------------------------------------------------------------------

class WatchCalendarRequest(BaseModel):
    entity_id: str = "placeholder"


@router.post("/watch")
async def start_calendar_watch(body: WatchCalendarRequest):
    """
    Instruct Composio to start watching the user's Google Calendar.
    Returns the trigger ID to use for disabling later.
    """
    import httpx

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            "https://backend.composio.dev/api/v1/triggers/enable",
            json={
                "triggerName": "google_calendar_event_created",
                "entityId": body.entity_id,
                "triggerConfig": {
                    "userId": "me",
                    "calendarId": "primary",
                },
            },
            headers={"x-api-key": settings.COMPOSIO_API_KEY},
        )
        if resp.status_code >= 400:
            raise HTTPException(status_code=502, detail=f"Composio error: {resp.text}")

    data = resp.json()
    logger.info("calendar_watch_started", trigger_id=data.get("triggerId"))
    return {"trigger_id": data.get("triggerId"), "status": "watching"}


@router.delete("/watch/{trigger_id}")
async def stop_calendar_watch(trigger_id: str):
    """Stop watching a user's calendar."""
    import httpx

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.delete(
            f"https://backend.composio.dev/api/v1/triggers/disable/{trigger_id}",
            headers={"x-api-key": settings.COMPOSIO_API_KEY},
        )
        resp.raise_for_status()

    logger.info("calendar_watch_stopped", trigger_id=trigger_id)
    return {"trigger_id": trigger_id, "status": "stopped"}


@router.get("/upcoming", response_model=list[dict])
async def list_upcoming(db: AsyncSession = Depends(get_db), limit: int = 20):
    """List scheduled meetings (status=scheduled) sorted by start time."""
    from datetime import UTC, datetime
    result = await db.execute(
        select(Meeting)
        .where(
            Meeting.status == "scheduled",
            Meeting.started_at >= datetime.now(UTC),
        )
        .order_by(Meeting.started_at.asc())
        .limit(limit)
    )
    meetings = result.scalars().all()
    return [
        {
            "id": m.id,
            "title": m.title,
            "platform": m.platform,
            "meeting_url": m.meeting_url,
            "started_at": m.started_at.isoformat() if m.started_at else None,
            "series_id": m.series_id,
        }
        for m in meetings
    ]
