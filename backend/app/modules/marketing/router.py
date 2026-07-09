import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user_id, get_session
from app.modules.marketing.service import (
    create_campaign,
    create_social_automation,
    get_social_post_log,
    generate_campaign_content,
    list_social_post_logs,
    list_campaigns,
    list_social_automations,
    run_social_automation_once,
    set_social_automation_active,
)

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


class SocialAutomationCreate(BaseModel):
    name: str
    platform_connection_id: uuid.UUID
    campaign_id: uuid.UUID | None = None
    schedule_minutes: int = 120
    publisher_type: str = "webhook_bridge"
    content_template: str | None = None
    content_config: dict = Field(default_factory=dict)
    publisher_config: dict = Field(default_factory=dict)


class SocialAutomationResponse(BaseModel):
    id: uuid.UUID
    name: str
    platform_connection_id: uuid.UUID
    campaign_id: uuid.UUID | None
    platform: str
    publisher_type: str
    is_active: bool
    schedule_minutes: int
    next_run_at: datetime | None
    last_run_at: datetime | None
    last_status: str | None
    last_error: str | None

    model_config = {"from_attributes": True}


class SocialAutomationListResponse(BaseModel):
    items: list[SocialAutomationResponse]
    total: int


class SocialAutomationRunResponse(BaseModel):
    id: uuid.UUID
    status: str
    platform: str
    posted_at: str
    error_message: str | None


class SocialAutomationUpdateActiveRequest(BaseModel):
    is_active: bool


class SocialPostLogResponse(BaseModel):
    id: uuid.UUID
    automation_id: uuid.UUID
    platform: str
    status: str
    request_payload: dict
    response_payload: dict
    error_message: str | None
    posted_at: datetime

    model_config = {"from_attributes": True}


class SocialPostLogListResponse(BaseModel):
    items: list[SocialPostLogResponse]
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


@router.post("/social-automations", response_model=SocialAutomationResponse, status_code=201)
async def create_social_automation_endpoint(
    data: SocialAutomationCreate,
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    automation = await create_social_automation(
        session,
        user_id,
        name=data.name,
        platform_connection_id=data.platform_connection_id,
        campaign_id=data.campaign_id,
        schedule_minutes=data.schedule_minutes,
        publisher_type=data.publisher_type,
        content_template=data.content_template,
        content_config=data.content_config,
        publisher_config=data.publisher_config,
    )
    return automation


@router.get("/social-automations", response_model=SocialAutomationListResponse)
async def list_social_automations_endpoint(
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    items, total = await list_social_automations(session, user_id, offset, limit)
    return SocialAutomationListResponse(items=items, total=total)


@router.post("/social-automations/{automation_id}/run", response_model=SocialAutomationRunResponse)
async def run_social_automation_endpoint(
    automation_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    log_item = await run_social_automation_once(session, user_id, automation_id)
    return SocialAutomationRunResponse(
        id=log_item.id,
        status=log_item.status,
        platform=log_item.platform,
        posted_at=log_item.posted_at.isoformat(),
        error_message=log_item.error_message,
    )


@router.patch("/social-automations/{automation_id}/active", response_model=SocialAutomationResponse)
async def update_social_automation_active_endpoint(
    automation_id: uuid.UUID,
    data: SocialAutomationUpdateActiveRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    automation = await set_social_automation_active(session, user_id, automation_id, data.is_active)
    return automation


@router.get("/social-post-logs", response_model=SocialPostLogListResponse)
async def list_social_post_logs_endpoint(
    automation_id: uuid.UUID | None = Query(default=None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    items, total = await list_social_post_logs(
        session=session,
        user_id=user_id,
        automation_id=automation_id,
        offset=offset,
        limit=limit,
    )
    return SocialPostLogListResponse(items=items, total=total)


@router.get("/social-post-logs/{log_id}", response_model=SocialPostLogResponse)
async def get_social_post_log_endpoint(
    log_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    return await get_social_post_log(session, user_id, log_id)
