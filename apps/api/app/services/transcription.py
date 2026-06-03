"""Whisper fallback for manual audio uploads."""
import io

from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.core.logging import logger

openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

SUPPORTED_FORMATS = {".mp3", ".mp4", ".mpeg", ".mpga", ".m4a", ".wav", ".webm", ".ogg"}
MAX_FILE_SIZE_MB = 25


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def transcribe_audio(audio_bytes: bytes, filename: str) -> str:
    """Send audio to OpenAI Whisper and return plain-text transcript."""
    log = logger.bind(filename=filename, size_kb=len(audio_bytes) // 1024)
    log.info("whisper_transcription_started")

    audio_file = io.BytesIO(audio_bytes)
    audio_file.name = filename

    response = await openai_client.audio.transcriptions.create(
        model="whisper-1",
        file=audio_file,
        response_format="verbose_json",
        timestamp_granularities=["segment"],
    )

    # Build speaker-labelled transcript from segments (no diarization in Whisper,
    # so we just output time-coded text; Recall.ai provides real diarization)
    lines = []
    for seg in response.segments or []:
        start = _fmt_time(seg.start)
        lines.append(f"[{start}] {seg.text.strip()}")

    transcript = "\n".join(lines)
    log.info("whisper_transcription_done", segments=len(lines))
    return transcript


def _fmt_time(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    return f"{m:02d}:{s:02d}"
