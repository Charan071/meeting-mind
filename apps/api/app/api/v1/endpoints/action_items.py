from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.models.action_item import ActionItem
from app.schemas.action_item import ActionItemResponse, ActionItemUpdate
from app.services.state_machine import InvalidTransitionError, validate_transition

router = APIRouter(prefix="/action-items", tags=["action-items"])

DbDep = Annotated[AsyncSession, Depends(get_db)]


@router.get("/", response_model=list[ActionItemResponse])
async def list_action_items(
    db: DbDep,
    status: str | None = None,
    owner_email: str | None = None,
    meeting_id: str | None = None,
    skip: int = 0,
    limit: int = 100,
):
    query = select(ActionItem)
    if status:
        query = query.where(ActionItem.status == status)
    if owner_email:
        query = query.where(ActionItem.owner_email == owner_email)
    if meeting_id:
        query = query.where(ActionItem.meeting_id == meeting_id)
    query = query.order_by(ActionItem.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/overdue", response_model=list[ActionItemResponse])
async def list_overdue(db: DbDep, limit: int = 50):
    """All overdue items — used by the manager view."""
    result = await db.execute(
        select(ActionItem)
        .where(ActionItem.status == "overdue")
        .order_by(ActionItem.created_at)
        .limit(limit)
    )
    return result.scalars().all()


@router.get("/open", response_model=list[ActionItemResponse])
async def list_open(db: DbDep, owner_email: str | None = None, limit: int = 100):
    """All open/in-progress items — manager commitment view."""
    query = select(ActionItem).where(
        ActionItem.status.in_(["open", "in_progress", "overdue"])
    )
    if owner_email:
        query = query.where(ActionItem.owner_email == owner_email)
    query = query.order_by(ActionItem.status, ActionItem.deadline.asc().nulls_last())
    result = await db.execute(query.limit(limit))
    return result.scalars().all()


@router.get("/{item_id}", response_model=ActionItemResponse)
async def get_action_item(item_id: str, db: DbDep):
    item = await db.get(ActionItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Action item not found")
    return item


@router.patch("/{item_id}", response_model=ActionItemResponse)
async def update_action_item(item_id: str, body: ActionItemUpdate, db: DbDep):
    item = await db.get(ActionItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Action item not found")

    # Enforce state machine for status transitions
    if body.status and body.status != item.status:
        try:
            validate_transition(item.status, body.status)
        except InvalidTransitionError as e:
            raise HTTPException(status_code=422, detail=str(e))

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(item, field, value)

    await db.commit()
    await db.refresh(item)
    return item


@router.post("/{item_id}/done", response_model=ActionItemResponse)
async def mark_done(item_id: str, db: DbDep):
    """Quick mark-done — validates state machine."""
    item = await db.get(ActionItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Action item not found")
    try:
        validate_transition(item.status, "done")
    except InvalidTransitionError as e:
        raise HTTPException(status_code=422, detail=str(e))
    item.status = "done"
    await db.commit()
    await db.refresh(item)
    return item
