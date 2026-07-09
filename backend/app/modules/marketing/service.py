"""Marketing automation — ad copy generation, SEO, campaign management."""

import logging
import uuid
from copy import deepcopy
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.agents.marketing_agent import generate_ad_copy, generate_seo_keywords, generate_social_post
from app.core.security import decrypt_credentials
from app.integrations.social_publishers.registry import SocialPublisherRegistry
from app.modules.marketing.models import (
    AITask,
    CampaignStatus,
    CampaignType,
    MarketingCampaign,
    SocialAutomation,
    SocialPostLog,
)
from app.modules.products.models import PlatformConnection

logger = logging.getLogger(__name__)

_SENSITIVE_KEYS = {
    "access_token",
    "refresh_token",
    "app_secret",
    "client_secret",
    "secret",
    "token",
    "authorization",
    "password",
}


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


def _next_run_at(minutes: int) -> datetime:
    return datetime.now(timezone.utc) + timedelta(minutes=max(1, minutes))


def _redact_sensitive(value):
    if isinstance(value, dict):
        redacted = {}
        for key, item in value.items():
            if str(key).lower() in _SENSITIVE_KEYS:
                redacted[key] = "***"
            else:
                redacted[key] = _redact_sensitive(item)
        return redacted
    if isinstance(value, list):
        return [_redact_sensitive(item) for item in value]
    return value


def _build_log_payload(publish_payload: dict) -> dict:
    safe_payload = deepcopy(publish_payload)
    return _redact_sensitive(safe_payload)


def _normalize_publish_response(response_payload: object) -> dict:
    if isinstance(response_payload, dict):
        return response_payload
    return {"raw": response_payload}


async def create_social_automation(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    name: str,
    platform_connection_id: uuid.UUID,
    campaign_id: uuid.UUID | None,
    schedule_minutes: int,
    publisher_type: str,
    content_template: str | None,
    content_config: dict | None,
    publisher_config: dict | None,
) -> SocialAutomation:
    conn = await session.get(PlatformConnection, platform_connection_id)
    if conn is None or conn.user_id != user_id:
        from app.core.exceptions import NotFoundError

        raise NotFoundError("Platform connection not found")

    automation = SocialAutomation(
        user_id=user_id,
        platform_connection_id=platform_connection_id,
        campaign_id=campaign_id,
        name=name,
        platform=conn.platform.value,
        publisher_type=publisher_type,
        schedule_minutes=schedule_minutes,
        next_run_at=_next_run_at(schedule_minutes),
        content_template=content_template,
        content_config=content_config or {},
        publisher_config=publisher_config or {},
    )
    session.add(automation)
    await session.flush()
    return automation


async def list_social_automations(
    session: AsyncSession,
    user_id: uuid.UUID,
    offset: int = 0,
    limit: int = 50,
) -> tuple[list[SocialAutomation], int]:
    query = (
        select(SocialAutomation)
        .where(SocialAutomation.user_id == user_id)
        .order_by(SocialAutomation.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    count_query = select(func.count()).select_from(SocialAutomation).where(SocialAutomation.user_id == user_id)
    result = await session.execute(query)
    total = (await session.execute(count_query)).scalar_one()
    return list(result.scalars().all()), total


async def _build_social_payload(session: AsyncSession, automation: SocialAutomation) -> dict:
    product_title = automation.content_config.get("product_title") or automation.name
    product_description = automation.content_config.get("product_description") or ""
    tone = automation.content_config.get("tone") or "casual"

    if automation.campaign_id:
        campaign = await session.get(MarketingCampaign, automation.campaign_id)
        if campaign is not None:
            ad_copy = campaign.ad_copy or {}
            if isinstance(ad_copy.get("descriptions"), list) and ad_copy.get("descriptions"):
                product_description = str(ad_copy["descriptions"][0])
            product_title = campaign.name

    generated = await generate_social_post(
        product_title=product_title,
        product_description=product_description,
        platform=automation.platform,
        tone=tone,
    )

    caption = str(generated.get("caption") or "").strip()
    hashtags = generated.get("hashtags") or []
    media_urls = automation.content_config.get("media_urls") or []

    if automation.content_template:
        caption = automation.content_template.replace("{caption}", caption)

    return {
        "platform": automation.platform,
        "caption": caption,
        "hashtags": hashtags,
        "media_urls": media_urls,
        "call_to_action": generated.get("call_to_action") or "",
    }


async def run_social_automation_once(
    session: AsyncSession,
    user_id: uuid.UUID,
    automation_id: uuid.UUID,
) -> SocialPostLog:
    automation = await session.get(SocialAutomation, automation_id)
    if automation is None or automation.user_id != user_id:
        from app.core.exceptions import NotFoundError

        raise NotFoundError("Social automation not found")

    conn = await session.get(PlatformConnection, automation.platform_connection_id)
    if conn is None:
        from app.core.exceptions import NotFoundError

        raise NotFoundError("Platform connection not found")

    publish_payload = await _build_social_payload(session, automation)
    publish_payload["credentials"] = decrypt_credentials(conn.credentials)
    publish_payload["region"] = conn.region
    log_payload = _build_log_payload(publish_payload)

    publisher = SocialPublisherRegistry.get_publisher(
        automation.publisher_type,
        automation.publisher_config,
    )

    try:
        response_payload = _normalize_publish_response(await publisher.publish(publish_payload))
        status = "success"
        error_message = None
        automation.last_status = "success"
        automation.last_error = None
    except Exception as exc:
        response_payload = {"ok": False, "error": str(exc)[:1000]}
        status = "error"
        error_message = str(exc)[:1000]
        automation.last_status = "error"
        automation.last_error = error_message

    automation.last_run_at = datetime.now(timezone.utc)
    if automation.is_active:
        automation.next_run_at = _next_run_at(automation.schedule_minutes)

    log_item = SocialPostLog(
        automation_id=automation.id,
        user_id=automation.user_id,
        platform=automation.platform,
        status=status,
        request_payload=log_payload,
        response_payload=response_payload,
        error_message=error_message,
    )
    session.add(log_item)
    await session.flush()

    if status == "error" and automation.is_active:
        threshold_raw = (automation.content_config or {}).get("max_consecutive_errors", 3)
        try:
            threshold = max(2, int(threshold_raw))
        except (TypeError, ValueError):
            threshold = 3

        recent_stmt = (
            select(SocialPostLog.status)
            .where(SocialPostLog.automation_id == automation.id)
            .order_by(SocialPostLog.posted_at.desc())
            .limit(threshold)
        )
        recent_statuses = list((await session.execute(recent_stmt)).scalars().all())
        if len(recent_statuses) >= threshold and all(item == "error" for item in recent_statuses):
            automation.is_active = False
            automation.next_run_at = None
            automation.last_error = (
                f"Auto-paused after {threshold} consecutive failures. "
                f"Last error: {error_message or 'unknown'}"
            )

    return log_item


async def run_due_social_automations(session: AsyncSession) -> int:
    now = datetime.now(timezone.utc)
    query = (
        select(SocialAutomation)
        .where(
            SocialAutomation.is_active == True,
            SocialAutomation.next_run_at.isnot(None),
            SocialAutomation.next_run_at <= now,
        )
        .order_by(SocialAutomation.next_run_at.asc())
        .limit(50)
    )
    result = await session.execute(query)
    automations = list(result.scalars().all())

    done = 0
    for automation in automations:
        try:
            await run_social_automation_once(session, automation.user_id, automation.id)
            done += 1
        except Exception:
            continue
    return done


async def set_social_automation_active(
    session: AsyncSession,
    user_id: uuid.UUID,
    automation_id: uuid.UUID,
    is_active: bool,
) -> SocialAutomation:
    automation = await session.get(SocialAutomation, automation_id)
    if automation is None or automation.user_id != user_id:
        from app.core.exceptions import NotFoundError

        raise NotFoundError("Social automation not found")

    automation.is_active = is_active
    automation.next_run_at = _next_run_at(automation.schedule_minutes) if is_active else None
    await session.flush()
    return automation


async def list_social_post_logs(
    session: AsyncSession,
    user_id: uuid.UUID,
    automation_id: uuid.UUID | None = None,
    offset: int = 0,
    limit: int = 50,
) -> tuple[list[SocialPostLog], int]:
    filter_expr = SocialPostLog.user_id == user_id
    if automation_id is not None:
        filter_expr = filter_expr & (SocialPostLog.automation_id == automation_id)

    query = (
        select(SocialPostLog)
        .where(filter_expr)
        .order_by(SocialPostLog.posted_at.desc())
        .offset(offset)
        .limit(limit)
    )
    count_query = select(func.count()).select_from(SocialPostLog).where(filter_expr)
    result = await session.execute(query)
    total = (await session.execute(count_query)).scalar_one()
    return list(result.scalars().all()), total


async def get_social_post_log(
    session: AsyncSession,
    user_id: uuid.UUID,
    log_id: uuid.UUID,
) -> SocialPostLog:
    log_item = await session.get(SocialPostLog, log_id)
    if log_item is None or log_item.user_id != user_id:
        from app.core.exceptions import NotFoundError

        raise NotFoundError("Social post log not found")
    return log_item
