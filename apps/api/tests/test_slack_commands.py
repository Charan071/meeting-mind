"""Tests for /done and /defer Slack slash commands."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport

from app.main import app


@pytest.mark.asyncio
async def test_slack_done_missing_text():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/slack/commands",
            data={"command": "/done", "text": "", "user_name": "alice", "user_id": "U123"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    assert resp.status_code == 200
    assert "Usage" in resp.json()["text"]


@pytest.mark.asyncio
async def test_slack_done_unknown_item():
    with patch("app.api.v1.endpoints.slack_commands.AsyncSessionLocal") as MockSession:
        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=None)
        MockSession.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        MockSession.return_value.__aexit__ = AsyncMock(return_value=False)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/slack/commands",
                data={"command": "/done", "text": "nonexistent-id", "user_name": "alice", "user_id": "U123"},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
    assert resp.status_code == 200
    assert "not found" in resp.json()["text"].lower()


@pytest.mark.asyncio
async def test_slack_done_already_done():
    from app.models.action_item import ActionItem
    mock_item = MagicMock(spec=ActionItem)
    mock_item.status = "done"
    mock_item.task = "Write roadmap"

    with patch("app.api.v1.endpoints.slack_commands.AsyncSessionLocal") as MockSession:
        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=mock_item)
        MockSession.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        MockSession.return_value.__aexit__ = AsyncMock(return_value=False)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/slack/commands",
                data={"command": "/done", "text": "item-123", "user_name": "alice", "user_id": "U123"},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
    # State machine should reject done→done
    assert resp.status_code == 200
    body = resp.json()["text"]
    assert "cannot" in body.lower() or "terminal" in body.lower()
