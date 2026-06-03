"""Embedding service.

Provider priority:
  1. OpenAI text-embedding-3-small  (if OPENAI_API_KEY is set)
  2. Ollama nomic-embed-text        (local fallback, 768-dim)
"""
from __future__ import annotations

import struct

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.core.logging import logger

# Dimension changes by provider — pgvector column must match
EMBEDDING_DIM = 1536 if settings.OPENAI_API_KEY else 768  # nomic-embed-text = 768


def _use_openai() -> bool:
    return bool(settings.OPENAI_API_KEY)


# ── OpenAI ────────────────────────────────────────────────────────────────────

async def _embed_openai(texts: list[str]) -> list[list[float]]:
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    resp = await client.embeddings.create(
        model=settings.EMBEDDING_MODEL,
        input=[t[:8000] for t in texts],
    )
    return [item.embedding for item in resp.data]


# ── Ollama ────────────────────────────────────────────────────────────────────

async def _embed_ollama(texts: list[str]) -> list[list[float]]:
    vectors = []
    async with httpx.AsyncClient(timeout=60) as client:
        for text in texts:
            resp = await client.post(
                f"{settings.OLLAMA_BASE_URL}/api/embeddings",
                json={"model": settings.OLLAMA_EMBED_MODEL, "prompt": text[:8000]},
            )
            resp.raise_for_status()
            vectors.append(resp.json()["embedding"])
    return vectors


# ── Public API ────────────────────────────────────────────────────────────────

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
async def embed(text: str) -> list[float]:
    """Return an embedding vector for the given text."""
    results = await embed_batch([text])
    return results[0]


async def embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed multiple texts."""
    if not texts:
        return []
    provider = "openai" if _use_openai() else "ollama"
    logger.info("embedding_batch", provider=provider, count=len(texts))
    if _use_openai():
        return await _embed_openai(texts)
    return await _embed_ollama(texts)


# ── Utilities ─────────────────────────────────────────────────────────────────

def vector_to_bytes(vec: list[float]) -> bytes:
    return struct.pack(f"{len(vec)}f", *vec)


def bytes_to_vector(data: bytes) -> list[float]:
    n = len(data) // 4
    return list(struct.unpack(f"{n}f", data))


def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)
