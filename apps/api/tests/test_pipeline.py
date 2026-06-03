"""Integration test for extraction pipeline using a mock Claude response."""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.meeting import ClaudeExtractionOutput
from app.services.extraction import _parse_response


SAMPLE_TRANSCRIPT = """Alice: Good morning everyone. Let's kick off the Q3 planning.
Bob: I think we should prioritize the mobile app launch.
Alice: Agreed. Bob, can you own the roadmap by Friday?
Bob: Sure, I'll have the roadmap done by June 14th.
Charlie: What about the budget? That's still unresolved.
Alice: Good point. We decided to go with the $200K budget for mobile."""


MOCK_CLAUDE_RESPONSE = {
    "summary": "The team discussed Q3 priorities and agreed to focus on the mobile app launch. Bob was assigned to own the roadmap by June 14th. The $200K budget for mobile was approved.",
    "action_items": [
        {
            "task": "Write mobile app roadmap",
            "owner_name": "Bob",
            "owner_email": None,
            "deadline": "2026-06-14",
            "priority": "high",
            "verbatim_quote": "Bob, can you own the roadmap by Friday?",
        }
    ],
    "decisions": ["Go with $200K budget for mobile app"],
    "open_questions": [],
    "participants": ["Alice", "Bob", "Charlie"],
}


def test_parse_response_plain_json():
    result = _parse_response(json.dumps(MOCK_CLAUDE_RESPONSE))
    assert result["summary"].startswith("The team")


def test_parse_response_markdown_wrapped():
    wrapped = f"```json\n{json.dumps(MOCK_CLAUDE_RESPONSE)}\n```"
    result = _parse_response(wrapped)
    assert result["summary"].startswith("The team")


@pytest.mark.asyncio
async def test_extract_from_transcript_mocked():
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text=json.dumps(MOCK_CLAUDE_RESPONSE))]
    mock_message.usage = MagicMock(input_tokens=500, output_tokens=200, cache_read_input_tokens=0)

    with patch("app.services.extraction._client") as mock_client:
        mock_client.messages.create = AsyncMock(return_value=mock_message)

        from app.services.extraction import extract_from_transcript
        result = await extract_from_transcript(SAMPLE_TRANSCRIPT)

    assert isinstance(result, ClaudeExtractionOutput)
    assert len(result.action_items) == 1
    assert result.action_items[0].owner_name == "Bob"
    assert result.action_items[0].deadline == "2026-06-14"
    assert len(result.decisions) == 1
    assert "Alice" in result.participants
