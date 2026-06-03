"""Extraction service — transcript → structured intelligence.

Provider priority:
  1. Anthropic Claude  (if ANTHROPIC_API_KEY is set)
  2. Ollama            (local fallback, always available)
"""
import json
import re

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.core.logging import logger
from app.schemas.meeting import ClaudeExtractionOutput

EXTRACTION_SYSTEM = """You are MeetingMind's extraction engine. Given a meeting transcript, extract structured intelligence with surgical precision.

Rules:
- verbatim_quote: copy the EXACT words from the transcript, 1-2 sentences max
- owner_name: the person explicitly assigned or who volunteered; null if unclear
- deadline: ISO 8601 date (YYYY-MM-DD) if explicitly stated; null otherwise
- priority: critical=blocking/urgent, high=important this week, medium=default, low=nice-to-have
- decisions: things the group AGREED on (not just discussed)
- open_questions: unresolved items that need a follow-up answer
- summary: exactly 3 sentences covering what was discussed, what was decided, and what happens next

Return ONLY valid JSON — no markdown, no explanation."""

EXTRACTION_USER = """Extract structured data from this meeting transcript:

<transcript>
{transcript}
</transcript>

Return JSON matching this schema exactly:
{{
  "summary": "3 sentences: discussed / decided / next",
  "action_items": [
    {{
      "task": "specific, actionable task description",
      "owner_name": "string or null",
      "owner_email": null,
      "deadline": "YYYY-MM-DD or null",
      "priority": "low|medium|high|critical",
      "verbatim_quote": "exact transcript quote or null"
    }}
  ],
  "decisions": ["string", ...],
  "open_questions": ["string", ...],
  "participants": ["name", ...]
}}"""

_JSON_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


def _use_anthropic() -> bool:
    return bool(settings.ANTHROPIC_API_KEY)


def _parse_response(text: str) -> dict:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    m = _JSON_RE.search(text)
    if m:
        return json.loads(m.group(1))
    raise ValueError(f"Could not parse JSON from response: {text[:200]}")


async def _extract_anthropic(transcript: str) -> ClaudeExtractionOutput:
    import anthropic as _anthropic
    client = _anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    message = await client.messages.create(
        model=settings.CLAUDE_MODEL,
        max_tokens=4096,
        system=[
            {
                "type": "text",
                "text": EXTRACTION_SYSTEM,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": EXTRACTION_USER.format(transcript=transcript)}],
    )
    raw = message.content[0].text
    logger.info(
        "extraction_complete_anthropic",
        input_tokens=message.usage.input_tokens,
        output_tokens=message.usage.output_tokens,
        cache_read=getattr(message.usage, "cache_read_input_tokens", 0),
    )
    return ClaudeExtractionOutput(**_parse_response(raw))


async def _extract_ollama(transcript: str) -> ClaudeExtractionOutput:
    prompt = f"{EXTRACTION_SYSTEM}\n\n{EXTRACTION_USER.format(transcript=transcript)}"
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            f"{settings.OLLAMA_BASE_URL}/api/generate",
            json={
                "model": settings.OLLAMA_LLM_MODEL,
                "prompt": prompt,
                "stream": False,
                "format": "json",
            },
        )
        resp.raise_for_status()
        raw = resp.json()["response"]
    logger.info("extraction_complete_ollama", model=settings.OLLAMA_LLM_MODEL)
    return ClaudeExtractionOutput(**_parse_response(raw))


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=15),
    retry=retry_if_exception_type((json.JSONDecodeError, ValueError)),
)
async def extract_from_transcript(transcript: str) -> ClaudeExtractionOutput:
    log = logger.bind(transcript_chars=len(transcript))
    log.info("extraction_started", provider="anthropic" if _use_anthropic() else "ollama")

    if _use_anthropic():
        return await _extract_anthropic(transcript)
    return await _extract_ollama(transcript)
