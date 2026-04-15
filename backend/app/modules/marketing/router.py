import uuid

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user_id, get_session
from app.modules.marketing.service import create_campaign, generate_campaign_content, list_campaigns

router = APIRouter()


class CampaignCreate(BaseModel):
    name: str
    campaign_type: str
    budget_daily: float | None = None
    target_products: list[str] | None = None


class GenerateContentRequest(BaseModel):
    product_title: str
    product_description: str = ""
    target_audience: str = "general"


class CampaignResponse(BaseModel):
    id: uuid.UUID
    name: str
    campaign_type: str
    status: str
    budget_daily: float | None
    ad_copy: dict
    keywords: list
    is_ai_generated: bool

    model_config = {"from_attributes": True}


class CampaignListResponse(BaseModel):
    items: list[CampaignResponse]
    total: int


@router.post("/campaigns", response_model=CampaignResponse, status_code=201)
async def create(
    data: CampaignCreate,
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    return await create_campaign(session, user_id, data.name, data.campaign_type, data.budget_daily, data.target_products)


@router.get("/campaigns", response_model=CampaignListResponse)
async def list_all(
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    items, total = await list_campaigns(session, user_id, offset, limit)
    return CampaignListResponse(items=items, total=total)


@router.post("/campaigns/{campaign_id}/generate")
async def generate_content(
    campaign_id: uuid.UUID,
    data: GenerateContentRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    return await generate_campaign_content(
        session, user_id, campaign_id, data.product_title, data.product_description, data.target_audience
    )
