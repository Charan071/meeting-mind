"""Unit tests for Claude extraction schema validation."""
import json
import pytest
from app.schemas.meeting import ClaudeExtractionOutput


def test_extraction_schema_valid():
    data = {
        "summary": "The team discussed Q3 goals and agreed on priorities.",
        "action_items": [
            {
                "task": "Write Q3 OKRs",
                "owner_name": "Alice",
                "owner_email": None,
                "deadline": "2026-06-15",
                "priority": "high",
                "verbatim_quote": "Alice will write the Q3 OKRs by end of next week",
            }
        ],
        "decisions": ["Move launch to July"],
        "open_questions": ["What is the budget for marketing?"],
        "participants": ["Alice", "Bob"],
    }
    result = ClaudeExtractionOutput(**data)
    assert len(result.action_items) == 1
    assert result.action_items[0].owner_name == "Alice"
    assert result.action_items[0].priority == "high"


def test_extraction_schema_defaults():
    data = {
        "summary": "Short meeting.",
        "action_items": [{"task": "Do something"}],
        "decisions": [],
        "open_questions": [],
        "participants": [],
    }
    result = ClaudeExtractionOutput(**data)
    assert result.action_items[0].priority == "medium"
    assert result.action_items[0].owner_name is None


def test_extraction_schema_rejects_missing_summary():
    with pytest.raises(Exception):
        ClaudeExtractionOutput(
            action_items=[],
            decisions=[],
            open_questions=[],
            participants=[],
        )
