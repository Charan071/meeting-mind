from datetime import datetime

from pydantic import BaseModel, HttpUrl


class MeetingCreate(BaseModel):
    title: str
    meeting_url: str | None = None
    platform: str | None = None
    started_at: datetime | None = None


class MeetingUpdate(BaseModel):
    title: str | None = None
    status: str | None = None
    summary_short: str | None = None


class MeetingResponse(BaseModel):
    id: str
    title: str
    status: str
    platform: str | None
    meeting_url: str | None
    recall_bot_id: str | None
    summary_short: str | None
    started_at: datetime | None
    ended_at: datetime | None
    duration_seconds: int | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ExtractionResponse(BaseModel):
    id: str
    meeting_id: str
    summary: str
    decisions: list[str]
    open_questions: list[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class ClaudeExtractionOutput(BaseModel):
    """Structured output schema for Claude extraction."""
    summary: str
    action_items: list["ActionItemExtracted"]
    decisions: list[str]
    open_questions: list[str]
    participants: list[str]


class ActionItemExtracted(BaseModel):
    task: str
    owner_name: str | None = None
    owner_email: str | None = None
    deadline: str | None = None
    priority: str = "medium"
    verbatim_quote: str | None = None
