"""Storage stub — transcripts are stored in Postgres (MeetingExtraction.raw_transcript).
S3 upload can be wired in later by restoring the boto3 implementation."""
import uuid

from app.core.logging import logger


def upload_audio(audio_bytes: bytes, filename: str) -> str:
    key = f"audio/{uuid.uuid4()}/{filename}"
    logger.info("audio_storage_skipped", key=key, size_kb=len(audio_bytes) // 1024)
    return f"local://{key}"


def upload_transcript(transcript: str, meeting_id: str) -> str:
    logger.info("transcript_storage_skipped", meeting_id=meeting_id)
    return f"local://transcripts/{meeting_id}/transcript.txt"
