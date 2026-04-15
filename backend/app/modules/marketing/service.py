"""Marketing automation — ad copy generation, SEO, campaign management."""

import logging
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.agents.marketing_agent import generate_ad_copy, generate_seo_keywords, generate_social_post
from app.modules.marketing.models import AITask, CampaignStatus, CampaignType, MarketingCampaign

logger = logging.getLogger(__name__)


async def create_campaign(
    session: AsyncSession,
    user_id: uuid.UUID,
    name: str,
    campaign_type: str,
    budget_daily: float | None = None,
    target_products: list | None = None,
) -> MarketingCampaign:
    campaign = MarketingCampaign(
        user_id=user_id,
        name=name,
        campaign_type=CampaignType(campaign_type),
        budget_daily=budget_daily,
        target_products=target_products or [],
    )
    session.add(campaign)
    await session.flush()
    return campaign


async def generate_campaign_content(
    session: AsyncSession,
    user_id: uuid.UUID,
    campaign_id: uuid.UUID,
    product_title: str,
    product_description: str,
    target_audience: str = "general",
) -> dict:
    """Use AI to generate ad copy and keywords for a campaign."""
    campaign = await session.get(MarketingCampaign, campaign_id)
    if not campaign:
        from app.core.exceptions import NotFoundError
        raise NotFoundError("Campaign not found")

    # Track the AI task
    task = AITask(
        user_id=user_id,
        task_type="generate_campaign_content",
        input_data={
            "campaign_id": str(campaign_id),
            "product_title": product_title,
            "campaign_type": campaign.campaign_type.value,
        },
    )
    session.add(task)

    try:
        # Generate ad copy
        ad_result = await generate_ad_copy(
            product_title=product_title,
            product_description=product_description,
            platform=campaign.campaign_type.value,
            target_audience=target_audience,
        )

        # Generate SEO keywords
        seo_result = await generate_seo_keywords(
            product_title=product_title,
            category=target_audience,
        )

        campaign.ad_copy = {
            "headlines": ad_result.get("headlines", []),
            "descriptions": ad_result.get("descriptions", []),
        }
        campaign.keywords = seo_result.get("keywords", [])
        campaign.is_ai_generated = True

        task.status = "completed"
        task.output_data = {"ad_copy": campaign.ad_copy, "keywords": campaign.keywords}
        task.model_used = ad_result.get("model", "")
        task.tokens_used = ad_result.get("tokens", 0)
        task.cost_usd = ad_result.get("cost", 0.0)

    except Exception as e:
        logger.error("Campaign content generation failed: %s", e)
        task.status = "failed"
        task.error_message = str(e)

    await session.flush()
    return {"ad_copy": campaign.ad_copy, "keywords": campaign.keywords}


async def list_campaigns(
    session: AsyncSession,
    user_id: uuid.UUID,
    offset: int = 0,
    limit: int = 50,
) -> tuple[list[MarketingCampaign], int]:
    query = (
        select(MarketingCampaign)
        .where(MarketingCampaign.user_id == user_id)
        .order_by(MarketingCampaign.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    count_query = (
        select(func.count())
        .select_from(MarketingCampaign)
        .where(MarketingCampaign.user_id == user_id)
    )
    result = await session.execute(query)
    total = (await session.execute(count_query)).scalar_one()
    return list(result.scalars().all()), total
