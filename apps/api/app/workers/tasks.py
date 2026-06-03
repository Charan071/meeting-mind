"""Celery tasks — async processing pipeline."""
import asyncio
import json
from datetime import UTC, datetime

from app.core.logging import logger
from app.workers.celery_app import celery_app


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ---------------------------------------------------------------------------
# Core pipeline: transcript → extraction → storage → resolution → integrations → WS
# ---------------------------------------------------------------------------

@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name="app.workers.tasks.process_meeting_transcript",
    acks_late=True,
)
def process_meeting_transcript(self, meeting_id: str, transcript: str) -> dict:
    log = logger.bind(meeting_id=meeting_id, task_id=self.request.id)
    log.info("pipeline_started")
    try:
        result = _run(_pipeline(meeting_id, transcript, log))
        log.info("pipeline_succeeded", **result)
        return result
    except Exception as exc:
        log.error("pipeline_failed", error=str(exc))
        raise self.retry(exc=exc)


async def _pipeline(meeting_id: str, transcript: str, log) -> dict:
    from sqlalchemy import select

    from app.core.websocket import manager
    from app.db.base import AsyncSessionLocal
    from app.models.action_item import ActionItem
    from app.models.integration import IntegrationSettings
    from app.models.meeting import Meeting, MeetingExtraction, Participant
    from app.services.extraction import extract_from_transcript
    from app.services.integrations import fire_integrations
    from app.services.resolution import detect_resolutions, store_action_item_embeddings
    from app.services.storage import upload_transcript

    # 1 — Claude extraction
    extraction = await extract_from_transcript(transcript)
    log.info("extraction_done", action_items=len(extraction.action_items))

    db_meeting = db_extraction = None
    db_action_items: list[ActionItem] = []
    owner_id = "placeholder"

    async with AsyncSessionLocal() as db:
        meeting = await db.get(Meeting, meeting_id)
        if not meeting:
            raise ValueError(f"Meeting {meeting_id} not found")
        owner_id = meeting.owner_id

        # 2 — Persist extraction
        meeting.status = "completed"
        meeting.summary_short = extraction.summary
        db_meeting = meeting

        db_extraction = MeetingExtraction(
            meeting_id=meeting_id,
            summary=extraction.summary,
            decisions=json.dumps(extraction.decisions),
            open_questions=json.dumps(extraction.open_questions),
            raw_transcript=transcript,
        )
        db.add(db_extraction)

        for item in extraction.action_items:
            ai = ActionItem(
                meeting_id=meeting_id,
                task=item.task,
                owner_name=item.owner_name,
                owner_email=item.owner_email,
                priority=item.priority,
                verbatim_quote=item.verbatim_quote,
                status="open",
            )
            db.add(ai)
            db_action_items.append(ai)

        await db.commit()
        for obj in [db_extraction] + db_action_items:
            await db.refresh(obj)
        await db.refresh(meeting)

        # 3 — Embed new action items (Phase 3 — resolution detection prerequisite)
        await store_action_item_embeddings(db, db_action_items)

        # 4 — Detect if any previously open items were resolved in this meeting
        resolved_ids = await detect_resolutions(db, meeting_id, transcript, owner_id)
        if resolved_ids:
            log.info("resolutions_detected", count=len(resolved_ids), ids=resolved_ids)

        # 5 — Load integration settings + participant emails
        settings_result = await db.execute(
            select(IntegrationSettings).where(IntegrationSettings.user_id == owner_id)
        )
        settings_row = settings_result.scalar_one_or_none()

        participants_result = await db.execute(
            select(Participant).where(Participant.meeting_id == meeting_id)
        )
        participant_emails = [p.email for p in participants_result.scalars().all() if p.email]

    # 6 — S3 transcript upload (non-fatal)
    try:
        url = upload_transcript(transcript, meeting_id)
        async with AsyncSessionLocal() as db:
            m = await db.get(Meeting, meeting_id)
            if m:
                m.transcript_url = url
                await db.commit()
    except Exception as e:
        log.warning("transcript_upload_failed", error=str(e))

    # 7 — Fire integrations in parallel
    await fire_integrations(
        owner_id=owner_id,
        meeting=db_meeting,
        extraction=db_extraction,
        action_items=db_action_items,
        settings_row=settings_row,
        participant_emails=participant_emails,
    )

    # 8 — WebSocket push
    await manager.broadcast(meeting_id, {
        "event": "meeting.completed",
        "meeting_id": meeting_id,
        "summary": extraction.summary,
        "action_items": len(db_action_items),
        "resolved": len(resolved_ids) if resolved_ids else 0,
    })

    return {
        "meeting_id": meeting_id,
        "action_items": len(db_action_items),
        "resolved": len(resolved_ids) if resolved_ids else 0,
    }


# ---------------------------------------------------------------------------
# Auto-join — fires at meeting start_time (scheduled via Celery eta)
# ---------------------------------------------------------------------------

@celery_app.task(
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    name="app.workers.tasks.auto_join_meeting",
)
def auto_join_meeting(self, meeting_id: str) -> dict:
    """Dispatch a Recall.ai bot to auto-join a scheduled meeting."""
    log = logger.bind(meeting_id=meeting_id, task_id=self.request.id)
    log.info("auto_join_started")
    try:
        return _run(_auto_join(meeting_id, log))
    except Exception as exc:
        log.error("auto_join_failed", error=str(exc))
        raise self.retry(exc=exc)


async def _auto_join(meeting_id: str, log) -> dict:
    from app.db.base import AsyncSessionLocal
    from app.models.meeting import Meeting
    from app.services.recall import recall_client

    async with AsyncSessionLocal() as db:
        meeting = await db.get(Meeting, meeting_id)
        if not meeting:
            log.warning("auto_join_meeting_not_found")
            return {"skipped": True}

        if meeting.status not in ("scheduled",):
            log.info("auto_join_skipped", status=meeting.status)
            return {"skipped": True, "status": meeting.status}

        if not meeting.meeting_url:
            log.warning("auto_join_no_url")
            return {"skipped": True, "reason": "no_url"}

        bot = await recall_client.create_bot(meeting.meeting_url)
        meeting.recall_bot_id = bot["id"]
        meeting.status = "recording"
        await db.commit()

        log.info("auto_join_bot_dispatched", bot_id=bot["id"])

    # Notify owner via Slack DM that the bot joined
    await _notify_bot_joined(meeting, log)

    return {"meeting_id": meeting_id, "bot_id": bot["id"]}


async def _notify_bot_joined(meeting, log) -> None:
    from sqlalchemy import select
    from app.db.base import AsyncSessionLocal
    from app.models.integration import IntegrationSettings
    from app.services.composio import composio

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(IntegrationSettings).where(IntegrationSettings.user_id == meeting.owner_id)
        )
        row = result.scalar_one_or_none()

    if not row or not row.slack_enabled or not row.slack_channel_id:
        return

    try:
        await composio.send_slack_message(
            entity_id=meeting.owner_id,
            channel=row.slack_channel_id,
            text=f"🟢 MeetingMind bot has joined *{meeting.title}* and is now recording.",
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            f"🟢 *Bot joined*\n"
                            f"*{meeting.title}* is now being recorded.\n"
                            f"_You'll receive a digest when the call ends._"
                        ),
                    },
                }
            ],
        )
    except Exception as e:
        log.warning("bot_joined_notify_failed", error=str(e))


# ---------------------------------------------------------------------------
# Whisper fallback
# ---------------------------------------------------------------------------

@celery_app.task(
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    name="app.workers.tasks.process_audio_upload",
)
def process_audio_upload(self, meeting_id: str, audio_s3_url: str, filename: str) -> dict:
    log = logger.bind(meeting_id=meeting_id, filename=filename)
    log.info("whisper_pipeline_started")
    try:
        return _run(_whisper_pipeline(meeting_id, audio_s3_url, filename, log))
    except Exception as exc:
        log.error("whisper_pipeline_failed", error=str(exc))
        raise self.retry(exc=exc)


async def _whisper_pipeline(meeting_id: str, audio_s3_url: str, filename: str, log) -> dict:
    import httpx
    from app.db.base import AsyncSessionLocal
    from app.models.meeting import Meeting
    from app.services.transcription import transcribe_audio

    async with httpx.AsyncClient() as client:
        resp = await client.get(audio_s3_url, timeout=120)
        resp.raise_for_status()
        audio_bytes = resp.content

    log.info("audio_downloaded", size_kb=len(audio_bytes) // 1024)
    transcript = await transcribe_audio(audio_bytes, filename)

    async with AsyncSessionLocal() as db:
        meeting = await db.get(Meeting, meeting_id)
        if meeting:
            meeting.status = "processing"
            await db.commit()

    process_meeting_transcript.delay(meeting_id, transcript)
    return {"meeting_id": meeting_id, "transcript_chars": len(transcript)}


# ---------------------------------------------------------------------------
# Safety-net: scan for scheduled meetings that should have joined by now
# ---------------------------------------------------------------------------

@celery_app.task(name="app.workers.tasks.check_and_join_upcoming")
def check_and_join_upcoming() -> dict:
    """Every 5 min: find meetings due to start that haven't been joined yet."""
    return _run(_check_upcoming())


async def _check_upcoming() -> dict:
    from datetime import UTC, datetime, timedelta
    from sqlalchemy import select
    from app.db.base import AsyncSessionLocal
    from app.models.meeting import Meeting

    now = datetime.now(UTC)
    window_start = now - timedelta(minutes=5)
    window_end = now + timedelta(minutes=2)
    dispatched = 0

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Meeting).where(
                Meeting.status == "scheduled",
                Meeting.meeting_url.isnot(None),
                Meeting.started_at >= window_start,
                Meeting.started_at <= window_end,
                Meeting.recall_bot_id.is_(None),
            )
        )
        for meeting in result.scalars().all():
            auto_join_meeting.delay(meeting.id)
            dispatched += 1
            logger.info("safety_net_dispatched", meeting_id=meeting.id)

    return {"dispatched": dispatched}


# ---------------------------------------------------------------------------
# Weekly overdue nudge cron
# ---------------------------------------------------------------------------

@celery_app.task(name="app.workers.tasks.send_overdue_nudges")
def send_overdue_nudges() -> dict:
    log = logger.bind(task="send_overdue_nudges")
    log.info("nudge_job_started")
    count = _run(_nudge_pipeline(log))
    log.info("nudge_job_done", nudges_sent=count)
    return {"nudges_sent": count}


async def _nudge_pipeline(log) -> int:
    from sqlalchemy import select
    from app.db.base import AsyncSessionLocal
    from app.models.action_item import ActionItem
    from app.models.meeting import Meeting
    from app.services.nudge import send_nudge_dm

    now = datetime.now(UTC)
    count = 0

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(ActionItem).where(
                ActionItem.status == "open",
                ActionItem.deadline < now,
            )
        )
        overdue_items = result.scalars().all()

        for item in overdue_items:
            item.status = "overdue"

            # Load the source meeting for title + date context
            meeting = await db.get(Meeting, item.meeting_id)
            if not meeting:
                continue

            # Send Slack DM with verbatim quote
            sent = await send_nudge_dm(
                owner_id=meeting.owner_id,
                item=item,
                meeting=meeting,
            )
            if sent:
                count += 1
                log.info("nudge_sent", item_id=item.id, owner=item.owner_email)

        await db.commit()

    return count
