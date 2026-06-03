"""Composio integration service — wraps all outbound integration calls."""
from __future__ import annotations

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.core.logging import logger

COMPOSIO_BASE = "https://backend.composio.dev/api/v1"


class ComposioClient:
    """Thin async wrapper around the Composio REST API."""

    def __init__(self) -> None:
        self._headers = {
            "x-api-key": settings.COMPOSIO_API_KEY,
            "Content-Type": "application/json",
        }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _post(self, path: str, payload: dict) -> dict:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{COMPOSIO_BASE}{path}",
                json=payload,
                headers=self._headers,
            )
            resp.raise_for_status()
            return resp.json()

    # ------------------------------------------------------------------
    # Slack
    # ------------------------------------------------------------------

    async def send_slack_message(
        self,
        entity_id: str,
        channel: str,
        text: str,
        blocks: list[dict] | None = None,
    ) -> dict:
        log = logger.bind(entity_id=entity_id, channel=channel)
        log.info("slack_send_started")
        result = await self._post(
            "/actions/execute",
            {
                "actionName": "SLACK_SENDS_A_MESSAGE_TO_A_SLACK_CHANNEL",
                "entityId": entity_id,
                "input": {
                    "channel": channel,
                    "text": text,
                    **({"blocks": blocks} if blocks else {}),
                },
            },
        )
        log.info("slack_send_done")
        return result

    # ------------------------------------------------------------------
    # Gmail
    # ------------------------------------------------------------------

    async def send_email(
        self,
        entity_id: str,
        to: list[str],
        subject: str,
        body_html: str,
    ) -> dict:
        log = logger.bind(entity_id=entity_id, recipients=to)
        log.info("gmail_send_started")
        result = await self._post(
            "/actions/execute",
            {
                "actionName": "GMAIL_SEND_EMAIL",
                "entityId": entity_id,
                "input": {
                    "recipient_email": ", ".join(to),
                    "subject": subject,
                    "body": body_html,
                    "is_html": True,
                },
            },
        )
        log.info("gmail_send_done")
        return result

    # ------------------------------------------------------------------
    # Linear
    # ------------------------------------------------------------------

    async def create_linear_issue(
        self,
        entity_id: str,
        title: str,
        description: str,
        priority: int = 2,
    ) -> dict:
        log = logger.bind(entity_id=entity_id, title=title[:60])
        log.info("linear_issue_create_started")
        result = await self._post(
            "/actions/execute",
            {
                "actionName": "LINEAR_CREATE_LINEAR_ISSUE",
                "entityId": entity_id,
                "input": {
                    "title": title,
                    "description": description,
                    "priority": priority,  # 0=no priority, 1=urgent, 2=high, 3=medium, 4=low
                },
            },
        )
        log.info("linear_issue_created", issue_id=result.get("id"))
        return result

    # ------------------------------------------------------------------
    # Jira
    # ------------------------------------------------------------------

    async def create_jira_issue(
        self,
        entity_id: str,
        project_key: str,
        summary: str,
        description: str,
        priority: str = "Medium",
    ) -> dict:
        log = logger.bind(entity_id=entity_id, project=project_key)
        log.info("jira_issue_create_started")
        result = await self._post(
            "/actions/execute",
            {
                "actionName": "JIRA_CREATE_ISSUE",
                "entityId": entity_id,
                "input": {
                    "projectKey": project_key,
                    "summary": summary,
                    "description": description,
                    "issueType": "Task",
                    "priority": {"name": priority},
                },
            },
        )
        log.info("jira_issue_created")
        return result

    # ------------------------------------------------------------------
    # HubSpot
    # ------------------------------------------------------------------

    async def create_hubspot_note(
        self,
        entity_id: str,
        body: str,
        contact_ids: list[str] | None = None,
    ) -> dict:
        log = logger.bind(entity_id=entity_id)
        log.info("hubspot_note_create_started")
        result = await self._post(
            "/actions/execute",
            {
                "actionName": "HUBSPOT_CREATE_NOTE",
                "entityId": entity_id,
                "input": {
                    "properties": {
                        "hs_note_body": body,
                        "hs_timestamp": "now",
                    },
                    **({"associations": [{"to": {"id": cid}, "types": [{"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 202}]} for cid in (contact_ids or [])]} if contact_ids else {}),
                },
            },
        )
        log.info("hubspot_note_created")
        return result

    # ------------------------------------------------------------------
    # Salesforce
    # ------------------------------------------------------------------

    async def create_salesforce_task(
        self,
        entity_id: str,
        subject: str,
        description: str,
        who_id: str | None = None,
    ) -> dict:
        log = logger.bind(entity_id=entity_id)
        log.info("salesforce_task_create_started")
        result = await self._post(
            "/actions/execute",
            {
                "actionName": "SALESFORCE_CREATE_TASK",
                "entityId": entity_id,
                "input": {
                    "Subject": subject,
                    "Description": description,
                    "Status": "Not Started",
                    "Priority": "Normal",
                    **({"WhoId": who_id} if who_id else {}),
                },
            },
        )
        log.info("salesforce_task_created")
        return result


composio = ComposioClient()
