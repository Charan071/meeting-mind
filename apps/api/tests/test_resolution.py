"""Tests for cross-meeting resolution detection."""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.embeddings import cosine_similarity
from app.services.resolution import _chunk_transcript, _load_embedding


def test_cosine_similarity_identical():
    v = [1.0, 0.0, 0.0]
    assert cosine_similarity(v, v) == pytest.approx(1.0)


def test_cosine_similarity_orthogonal():
    a = [1.0, 0.0]
    b = [0.0, 1.0]
    assert cosine_similarity(a, b) == pytest.approx(0.0)


def test_cosine_similarity_zero_vector():
    assert cosine_similarity([0.0, 0.0], [1.0, 0.0]) == 0.0


def test_chunk_transcript_basic():
    transcript = "\n".join([f"Speaker: sentence {i}" for i in range(9)])
    chunks = _chunk_transcript(transcript, size=3)
    assert len(chunks) > 0
    assert all(isinstance(c, str) for c in chunks)


def test_chunk_transcript_empty():
    assert _chunk_transcript("", size=3) == []


def test_load_embedding_valid():
    vec = [0.1, 0.2, 0.3]
    result = _load_embedding(json.dumps(vec))
    assert result == pytest.approx(vec)


def test_load_embedding_none():
    assert _load_embedding(None) is None


def test_load_embedding_corrupt():
    assert _load_embedding("not-json{{") is None


@pytest.mark.asyncio
async def test_detect_resolutions_no_open_items():
    """With no open items, detect_resolutions should return [] immediately."""
    mock_db = MagicMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(return_value=mock_result)

    from app.services.resolution import detect_resolutions
    result = await detect_resolutions(mock_db, "meet-1", "Alice: done.", "user-1")
    assert result == []


@pytest.mark.asyncio
async def test_store_embeddings_empty():
    """store_action_item_embeddings with empty list is a no-op."""
    from app.services.resolution import store_action_item_embeddings
    mock_db = MagicMock()
    await store_action_item_embeddings(mock_db, [])
    mock_db.commit.assert_not_called()
