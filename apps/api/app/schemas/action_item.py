from datetime import datetime

from pydantic import BaseModel


class ActionItemResponse(BaseModel):
    id: str
    meeting_id: str
    task: str
    owner_name: str | None
    owner_email: str | None
    deadline: datetime | None
    priority: str
    status: str
    verbatim_quote: str | None
    resolved_in_meeting_id: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ActionItemUpdate(BaseModel):
    status: str | None = None
    owner_email: str | None = None
    deadline: datetime | None = None
    priority: str | None = None
