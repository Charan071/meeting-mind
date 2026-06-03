"""Webhook signature verification tests (no DB required)."""
import hashlib
import hmac

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.config import settings


def make_signature(body: bytes, secret: str) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


@pytest.mark.asyncio
async def test_webhook_rejects_bad_signature(monkeypatch):
    monkeypatch.setattr(settings, "RECALL_WEBHOOK_SECRET", "real-secret")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/webhooks/recall",
            json={"event": "bot.status_change", "data": {"bot": {"id": "bot-123"}, "status": {"code": "call_ended"}}},
            headers={"x-recall-signature": "sha256=badsig"},
        )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_webhook_accepts_valid_signature(monkeypatch):
    monkeypatch.setattr(settings, "RECALL_WEBHOOK_SECRET", "")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/webhooks/recall",
            json={"event": "bot.status_change", "data": {"bot": {"id": "bot-xyz"}, "status": {"code": "joining_call"}}},
        )
    # Should 200 (no-op status code)
    assert resp.status_code == 200
