from fastapi import APIRouter

from app.api.v1.endpoints.action_items import router as action_items_router
from app.api.v1.endpoints.calendar import router as calendar_router
from app.api.v1.endpoints.integrations import router as integrations_router
from app.api.v1.endpoints.meetings import router as meetings_router
from app.api.v1.endpoints.slack_commands import router as slack_router
from app.api.v1.endpoints.webhooks import router as webhooks_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(meetings_router)
api_router.include_router(action_items_router)
api_router.include_router(webhooks_router)
api_router.include_router(integrations_router)
api_router.include_router(slack_router)
api_router.include_router(calendar_router)
