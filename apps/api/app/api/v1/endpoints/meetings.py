import json
import os
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.websocket import manager
from app.db.base import get_db
from app.models.action_item import ActionItem
from app.models.meeting import Meeting, MeetingExtraction
from app.schemas.action_item import ActionItemResponse
from app.schemas.meeting import ExtractionResponse, MeetingCreate, MeetingResponse, MeetingUpdate
from app.services.recall import recall_client
from app.services.storage import upload_audio

router = APIRouter(prefix="/meetings", tags=["meetings"])

DbDep = Annotated[AsyncSession, Depends(get_db)]

WHISPER_MAX_BYTES = 25 * 1024 * 1024  # 25 MB


@router.get("/", response_model=list[MeetingResponse])
async def list_meetings(db: DbDep, skip: int = 0, limit: int = 50):
    result = await db.execute(
        select(Meeting).order_by(Meeting.created_at.desc()).offset(skip).limit(limit)
    )
    return result.scalars().all()


@router.post("/", response_model=MeetingResponse, status_code=status.HTTP_201_CREATED)
async def create_meeting(body: MeetingCreate, db: DbDep):
    meeting = Meeting(
        title=body.title,
        meeting_url=str(body.meeting_url) if body.meeting_url else None,
        platform=body.platform,
        started_at=body.started_at,
        status="scheduled",
        owner_id="placeholder",  # TODO: replace with JWT user
    )
    db.add(meeting)
    await db.commit()
    await db.refresh(meeting)
    return meeting


@router.get("/{meeting_id}", response_model=MeetingResponse)
async def get_meeting(meeting_id: str, db: DbDep):
    meeting = await db.get(Meeting, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return meeting


@router.patch("/{meeting_id}", response_model=MeetingResponse)
async def update_meeting(meeting_id: str, body: MeetingUpdate, db: DbDep):
    meeting = await db.get(Meeting, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(meeting, field, value)
    await db.commit()
    await db.refresh(meeting)
    return meeting


@router.post("/{meeting_id}/join", response_model=MeetingResponse)
async def join_meeting(meeting_id: str, db: DbDep):
    """Dispatch a Recall.ai bot to join the meeting."""
    meeting = await db.get(Meeting, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    if not meeting.meeting_url:
        raise HTTPException(status_code=400, detail="Meeting has no URL")

    bot = await recall_client.create_bot(meeting.meeting_url)
    meeting.recall_bot_id = bot["id"]
    meeting.status = "recording"
    await db.commit()
    await db.refresh(meeting)
    return meeting


@router.post("/{meeting_id}/upload-audio", response_model=MeetingResponse)
async def upload_audio_file(
    meeting_id: str,
    db: DbDep,
    file: UploadFile = File(...),
):
    """Whisper fallback: upload audio file to trigger transcription."""
    from app.workers.tasks import process_audio_upload

    meeting = await db.get(Meeting, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    ext = os.path.splitext(file.filename or "audio.mp3")[1].lower()
    allowed = {".mp3", ".mp4", ".mpeg", ".mpga", ".m4a", ".wav", ".webm", ".ogg"}
    if ext not in allowed:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {ext}")

    audio_bytes = await file.read()
    if len(audio_bytes) > WHISPER_MAX_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 25 MB)")

    # Upload to S3 then enqueue Whisper transcription
    s3_url = upload_audio(audio_bytes, file.filename or "upload.mp3")
    meeting.status = "processing"
    await db.commit()

    process_audio_upload.delay(meeting_id, s3_url, file.filename or "upload.mp3")

    await db.refresh(meeting)
    return meeting


@router.get("/{meeting_id}/extraction", response_model=ExtractionResponse)
async def get_extraction(meeting_id: str, db: DbDep):
    result = await db.execute(
        select(MeetingExtraction).where(MeetingExtraction.meeting_id == meeting_id)
    )
    extraction = result.scalar_one_or_none()
    if not extraction:
        raise HTTPException(status_code=404, detail="Extraction not available yet")

    # Deserialise JSON arrays stored as text
    return ExtractionResponse(
        id=extraction.id,
        meeting_id=extraction.meeting_id,
        summary=extraction.summary,
        decisions=json.loads(extraction.decisions),
        open_questions=json.loads(extraction.open_questions),
        created_at=extraction.created_at,
    )


@router.get("/{meeting_id}/action-items", response_model=list[ActionItemResponse])
async def get_meeting_action_items(meeting_id: str, db: DbDep):
    result = await db.execute(
        select(ActionItem)
        .where(ActionItem.meeting_id == meeting_id)
        .order_by(ActionItem.created_at)
    )
    return result.scalars().all()


@router.websocket("/{meeting_id}/ws")
async def meeting_ws(meeting_id: str, ws: WebSocket):
    """Subscribe to real-time events for a single meeting."""
    await manager.connect(meeting_id, ws)
    try:
        while True:
            # Keep alive — client can also send pings
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(meeting_id, ws)
