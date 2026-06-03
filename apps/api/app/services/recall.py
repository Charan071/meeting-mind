import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.core.logging import logger


class RecallClient:
    def __init__(self) -> None:
        self.base_url = settings.RECALL_BASE_URL
        self.headers = {
            "Authorization": f"Token {settings.RECALL_API_KEY}",
            "Content-Type": "application/json",
        }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def create_bot(self, meeting_url: str, bot_name: str = "MeetingMind") -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/bot",
                json={
                    "meeting_url": meeting_url,
                    "bot_name": bot_name,
                    "transcription_options": {"provider": "assembly_ai"},
                    "real_time_transcription": {
                        "destination_url": f"{settings.API_BASE_URL}/api/v1/webhooks/recall",
                    },
                    "webhook_url": f"{settings.API_BASE_URL}/api/v1/webhooks/recall",
                },
                headers=self.headers,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            logger.info("recall_bot_created", bot_id=data["id"], meeting_url=meeting_url)
            return data

    async def get_bot(self, bot_id: str) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/bot/{bot_id}",
                headers=self.headers,
                timeout=10,
            )
            resp.raise_for_status()
            return resp.json()

    async def get_transcript(self, bot_id: str) -> list[dict]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/bot/{bot_id}/transcript",
                headers=self.headers,
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()


recall_client = RecallClient()
