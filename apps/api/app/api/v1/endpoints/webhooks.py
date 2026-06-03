"""Recall.ai webhook receiver — validates signature, dispatches pipeline."""
import hashlib
import hmac

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select

from app.core.config import settings
from app.core.logging import logger
from app.db.base import AsyncSessionLocal
from app.models.meeting import Meeting

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

BOT_STATUS_DONE = {"call_ended", "done"}


def _verify_signature(body: bytes, header: str, secret: str) -> bool:
    """Verify Recall.ai HMAC-SHA256 signature (format: sha256=<hex>)."""
    expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header)


@router.post("/recall", status_code=status.HTTP_200_OK)
async def recall_webhook(request: Request):
    body = await request.body()

    if settings.RECALL_WEBHOOK_SECRET:
        sig = request.headers.get("x-recall-signature", "")
        if not _verify_signature(body, sig, settings.RECALL_WEBHOOK_SECRET):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")

    payload = await request.json()
    event: str = payload.get("event", "")
    bot_data: dict = payload.get("data", {}).get("bot", {})
    bot_id: str = bot_data.get("id", "")

    log = logger.bind(event=event, bot_id=bot_id)
    log.info("recall_webhook_received")

    if event == "bot.status_change":
        status_code: str = payload["data"].get("status", {}).get("code", "")
        log.info("bot_status_changed", status_code=status_code)

        if status_code in BOT_STATUS_DONE:
            await _handle_call_ended(bot_id, log)

    elif event == "transcript.data":
        words = payload.get("data", {}).get("transcript", {}).get("words", [])
        speaker = payload.get("data", {}).get("transcript", {}).get("speaker", "Unknown")
        text = " ".join(w.get("text", "") for w in words).strip()
        log.info("realtime_transcript_chunk", speaker=speaker, chars=len(text))

    return {"status": "ok"}


async def _handle_call_ended(bot_id: str, log) -> None:
    """Fetch transcript from Recall and enqueue the extraction pipeline."""
    from app.services.recall import recall_client
    from app.workers.tasks import process_meeting_transcript

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Meeting).where(Meeting.recall_bot_id == bot_id))
        meeting = result.scalar_one_or_none()

        if not meeting:
            log.warning("no_meeting_for_bot", bot_id=bot_id)
            return

        meeting.status = "processing"
        await db.commit()
        meeting_id = meeting.id

    # Fetch transcript from Recall.ai
    try:
        segments = await recall_client.get_transcript(bot_id)
        transcript = _format_transcript(segments)
    except Exception as e:
        log.error("transcript_fetch_failed", error=str(e))
        async with AsyncSessionLocal() as db:
            meeting = await db.get(Meeting, meeting_id)
            if meeting:
                meeting.status = "failed"
                await db.commit()
        return

    if not transcript.strip():
        log.warning("empty_transcript", meeting_id=meeting_id)
        async with AsyncSessionLocal() as db:
            meeting = await db.get(Meeting, meeting_id)
            if meeting:
                meeting.status = "failed"
                await db.commit()
        return

    # Enqueue async Celery job
    process_meeting_transcript.delay(meeting_id, transcript)
    log.info("pipeline_enqueued", meeting_id=meeting_id, transcript_chars=len(transcript))


def _format_transcript(segments: list[dict]) -> str:
    """Convert Recall.ai diarized segments into labelled plain text."""
    lines = []
    for seg in segments:
        speaker = seg.get("speaker") or "Unknown"
        words = seg.get("words") or []
        text = " ".join(w.get("text", "") for w in words).strip()
        if text:
            lines.append(f"{speaker}: {text}")
    return "\n".join(lines)
