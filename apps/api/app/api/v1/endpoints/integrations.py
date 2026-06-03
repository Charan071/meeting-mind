"""Integration management endpoints — connect, disconnect, settings."""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.models.integration import Integration, IntegrationSettings

router = APIRouter(prefix="/integrations", tags=["integrations"])

DbDep = Annotated[AsyncSession, Depends(get_db)]

PLACEHOLDER_USER = "placeholder"  # TODO: replace with JWT auth


class IntegrationSettingsUpdate(BaseModel):
    slack_enabled: bool | None = None
    slack_channel_id: str | None = None
    gmail_enabled: bool | None = None
    linear_enabled: bool | None = None
    jira_enabled: bool | None = None
    asana_enabled: bool | None = None
    hubspot_enabled: bool | None = None
    salesforce_enabled: bool | None = None


class IntegrationSettingsResponse(BaseModel):
    slack_enabled: bool
    slack_channel_id: str | None
    gmail_enabled: bool
    linear_enabled: bool
    jira_enabled: bool
    asana_enabled: bool
    hubspot_enabled: bool
    salesforce_enabled: bool

    model_config = {"from_attributes": True}


class IntegrationStatusResponse(BaseModel):
    provider: str
    status: str
    connected_at: str | None
    last_sync_at: str | None

    model_config = {"from_attributes": True}


@router.get("/", response_model=list[IntegrationStatusResponse])
async def list_integrations(db: DbDep):
    result = await db.execute(
        select(Integration).where(Integration.user_id == PLACEHOLDER_USER)
    )
    return result.scalars().all()


@router.get("/settings", response_model=IntegrationSettingsResponse)
async def get_settings(db: DbDep):
    result = await db.execute(
        select(IntegrationSettings).where(IntegrationSettings.user_id == PLACEHOLDER_USER)
    )
    row = result.scalar_one_or_none()
    if not row:
        # Return defaults
        return IntegrationSettingsResponse(
            slack_enabled=False,
            slack_channel_id=None,
            gmail_enabled=False,
            linear_enabled=False,
            jira_enabled=False,
            asana_enabled=False,
            hubspot_enabled=False,
            salesforce_enabled=False,
        )
    return row


@router.patch("/settings", response_model=IntegrationSettingsResponse)
async def update_settings(body: IntegrationSettingsUpdate, db: DbDep):
    result = await db.execute(
        select(IntegrationSettings).where(IntegrationSettings.user_id == PLACEHOLDER_USER)
    )
    row = result.scalar_one_or_none()

    if not row:
        row = IntegrationSettings(user_id=PLACEHOLDER_USER)
        db.add(row)

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(row, field, value)

    await db.commit()
    await db.refresh(row)
    return row


@router.post("/{provider}/connect")
async def connect_integration(provider: str, db: DbDep):
    """
    Returns a Composio OAuth URL for the user to authorise the integration.
    In production this proxies to Composio's /connectedAccounts initiate endpoint.
    """
    import httpx
    from app.core.config import settings

    valid = {"slack", "gmail", "linear", "jira", "asana", "hubspot", "salesforce", "google_calendar"}
    if provider not in valid:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                "https://backend.composio.dev/api/v1/connectedAccounts",
                json={
                    "integrationId": provider,
                    "entityId": PLACEHOLDER_USER,
                    "redirectUri": f"{settings.API_BASE_URL}/integrations/{provider}/callback",
                },
                headers={"x-api-key": settings.COMPOSIO_API_KEY},
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Composio error: {e}")

    return {"auth_url": data.get("redirectUrl"), "provider": provider}


@router.post("/{provider}/disconnect")
async def disconnect_integration(provider: str, db: DbDep):
    result = await db.execute(
        select(Integration).where(
            Integration.user_id == PLACEHOLDER_USER,
            Integration.provider == provider,
        )
    )
    row = result.scalar_one_or_none()
    if row:
        row.status = "disconnected"
        row.error_message = None
        await db.commit()

    return {"provider": provider, "status": "disconnected"}
