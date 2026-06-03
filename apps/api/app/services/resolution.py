"""Cross-meeting commitment resolution detection.

Algorithm:
1. For each sentence in the new transcript, compute embedding.
2. Cosine-similarity against all open action items' embeddings.
3. Any item with similarity >= RESOLUTION_THRESHOLD is a candidate.
4. Ask Claude: "Does this transcript segment confirm the task was completed?"
5. If yes → mark action item `done`, set resolved_in_meeting_id.
"""
from __future__ import annotations

import json

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger
from app.models.action_item import ActionItem
from app.services.embeddings import cosine_similarity, embed, embed_batch

RESOLUTION_THRESHOLD = 0.82  # cosine similarity floor for candidate matches
SENTENCE_CHUNK = 3  # sentences per chunk for embedding

CONFIRM_PROMPT = """You are reviewing meeting transcripts to check if a previously assigned task was completed.

Task: {task}
Owner: {owner}

New meeting transcript excerpt:
<excerpt>
{excerpt}
</excerpt>

Reply with JSON only:
{{"resolved": true/false, "confidence": 0.0-1.0, "reason": "one sentence"}}

resolved=true only if the excerpt EXPLICITLY states the task was done, delivered, or completed."""


async def detect_resolutions(
    db: AsyncSession,
    meeting_id: str,
    transcript: str,
    owner_id: str,
) -> list[str]:
    """
    Returns list of action item IDs that were resolved in this meeting.
    Updates their status + resolved_in_meeting_id in-place.
    """
    log = logger.bind(meeting_id=meeting_id)

    # Load all open action items for this user that have embeddings
    result = await db.execute(
        select(ActionItem).where(
            ActionItem.status.in_(["open", "in_progress"]),
            ActionItem.embedding_id.isnot(None),
        )
    )
    open_items = result.scalars().all()

    if not open_items:
        log.info("no_open_items_to_check")
        return []

    # Chunk transcript into overlapping sentence windows
    chunks = _chunk_transcript(transcript, size=SENTENCE_CHUNK)
    if not chunks:
        return []

    log.info("resolution_check_started", open_items=len(open_items), chunks=len(chunks))

    # Embed all chunks in one batch call
    chunk_embeddings = await embed_batch(chunks)

    # Load stored item embeddings (stored as JSON in embedding_id field)
    resolved_ids: list[str] = []

    for item in open_items:
        item_vec = _load_embedding(item.embedding_id)
        if item_vec is None:
            continue

        # Find the best-matching chunk
        best_sim = 0.0
        best_chunk = ""
        for chunk, chunk_vec in zip(chunks, chunk_embeddings):
            sim = cosine_similarity(item_vec, chunk_vec)
            if sim > best_sim:
                best_sim = sim
                best_chunk = chunk

        if best_sim < RESOLUTION_THRESHOLD:
            continue

        log.info("resolution_candidate", item_id=item.id, similarity=round(best_sim, 3))

        # Ask Claude to confirm
        confirmed = await _confirm_resolution(item, best_chunk)
        if confirmed:
            item.status = "done"
            item.resolved_in_meeting_id = meeting_id
            resolved_ids.append(item.id)
            log.info("resolution_confirmed", item_id=item.id, task=item.task[:60])

    if resolved_ids:
        await db.commit()

    log.info("resolution_check_done", resolved=len(resolved_ids))
    return resolved_ids


async def _confirm_resolution(item: ActionItem, excerpt: str) -> bool:
    prompt = CONFIRM_PROMPT.format(
        task=item.task,
        owner=item.owner_name or "unknown",
        excerpt=excerpt,
    )
    try:
        if settings.ANTHROPIC_API_KEY:
            import anthropic as _anthropic
            client = _anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
            msg = await client.messages.create(
                model=settings.CLAUDE_MODEL,
                max_tokens=256,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = msg.content[0].text.strip()
        else:
            async with httpx.AsyncClient(timeout=60) as client:
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
                raw = resp.json()["response"].strip()

        data = json.loads(raw)
        return bool(data.get("resolved")) and float(data.get("confidence", 0)) >= 0.7
    except Exception:
        return False


def _chunk_transcript(transcript: str, size: int = 3) -> list[str]:
    """Split transcript into overlapping windows of `size` lines."""
    lines = [l.strip() for l in transcript.splitlines() if l.strip()]
    chunks = []
    for i in range(0, len(lines), max(1, size - 1)):
        chunk = "\n".join(lines[i : i + size])
        if chunk:
            chunks.append(chunk)
    return chunks


def _load_embedding(embedding_id: str | None) -> list[float] | None:
    """Embedding stored as JSON string in embedding_id column."""
    if not embedding_id:
        return None
    try:
        return json.loads(embedding_id)
    except Exception:
        return None


async def store_action_item_embeddings(
    db: AsyncSession,
    action_items: list[ActionItem],
) -> None:
    """Embed each action item's task text and store in embedding_id."""
    if not action_items:
        return

    texts = [f"{ai.task}. Owner: {ai.owner_name or 'unassigned'}" for ai in action_items]
    vectors = await embed_batch(texts)

    for ai, vec in zip(action_items, vectors):
        ai.embedding_id = json.dumps(vec)

    await db.commit()
    logger.info("embeddings_stored", count=len(action_items))
