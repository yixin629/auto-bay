import uuid

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user_id, get_session
from app.modules.customer_service.service import approve_and_send, list_messages

router = APIRouter()


class MessageResponse(BaseModel):
    id: uuid.UUID
    platform: str
    direction: str
    sender: str | None
    body: str
    intent: str
    is_ai_generated: bool
    ai_confidence: float | None
    requires_human: bool
    ai_draft_response: str | None

    model_config = {"from_attributes": True}


class MessageListResponse(BaseModel):
    items: list[MessageResponse]
    total: int


class ApproveRequest(BaseModel):
    response_text: str | None = None


@router.get("/messages", response_model=MessageListResponse)
async def list_all_messages(
    requires_human: bool | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    items, total = await list_messages(session, user_id, requires_human, offset, limit)
    return MessageListResponse(items=items, total=total)


@router.post("/messages/{message_id}/approve", response_model=MessageResponse)
async def approve_message(
    message_id: uuid.UUID,
    data: ApproveRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    return await approve_and_send(session, message_id, data.response_text)
