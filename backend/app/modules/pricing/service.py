"""Pricing engine — rule-based dynamic pricing with exchange rate support.

Strategies: fixed, cost_plus, competitor_match, ai_dynamic.
LLM is NOT used here; pricing is deterministic.
"""

import logging
from decimal import Decimal

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.pricing.models import ExchangeRate, PriceHistory

logger = logging.getLogger(__name__)

# Platform fee estimates (percentage of sale price)
PLATFORM_FEES = {
    "ebay": Decimal("0.13"),       # ~13% final value fee
    "amazon": Decimal("0.15"),     # ~15% referral fee
    "shopify": Decimal("0.029"),   # 2.9% + $0.30 payment processing
    "tiktok": Decimal("0.05"),     # ~5% commission
}


async def get_exchange_rate(session: AsyncSession, base: str, target: str) -> Decimal:
    """Get the latest exchange rate from DB cache."""
    if base == target:
        return Decimal("1")

    result = await session.execute(
        select(ExchangeRate)
        .where(ExchangeRate.base_currency == base, ExchangeRate.target_currency == target)
        .order_by(ExchangeRate.fetched_at.desc())
        .limit(1)
    )
    rate = result.scalar_one_or_none()
    if rate:
        return Decimal(str(rate.rate))

    # Fallback: try inverse
    result = await session.execute(
        select(ExchangeRate)
        .where(ExchangeRate.base_currency == target, ExchangeRate.target_currency == base)
        .order_by(ExchangeRate.fetched_at.desc())
        .limit(1)
    )
    rate = result.scalar_one_or_none()
    if rate and rate.rate > 0:
        return Decimal("1") / Decimal(str(rate.rate))

    logger.warning("No exchange rate found for %s -> %s, using 1.0", base, target)
    return Decimal("1")


def calculate_cost_plus_price(
    base_cost: Decimal,
    cost_currency: str,
    target_currency: str,
    exchange_rate: Decimal,
    margin_pct: Decimal,
    platform: str,
    shipping_estimate: Decimal = Decimal("0"),
) -> Decimal:
    """Calculate selling price using cost-plus strategy.

    Formula: (cost_in_target_currency + shipping) / (1 - margin_pct - platform_fee_pct)
    This ensures the margin is on the final selling price, not cost.
    """
    cost_in_target = base_cost * exchange_rate
    platform_fee_pct = PLATFORM_FEES.get(platform, Decimal("0.10"))

    # Avoid division by zero
    denominator = Decimal("1") - margin_pct - platform_fee_pct
    if denominator <= 0:
        denominator = Decimal("0.01")

    price = (cost_in_target + shipping_estimate) / denominator
    return price.quantize(Decimal("0.01"))


def calculate_competitor_match_price(
    competitor_prices: list[Decimal],
    position: str = "below",  # "below", "match", "above"
    offset_pct: Decimal = Decimal("0.05"),
    floor_price: Decimal = Decimal("0"),
) -> Decimal:
    """Calculate price based on competitor positioning."""
    if not competitor_prices:
        return floor_price

    avg_price = sum(competitor_prices) / len(competitor_prices)
    min_price = min(competitor_prices)

    if position == "below":
        price = min_price * (Decimal("1") - offset_pct)
    elif position == "above":
        price = avg_price * (Decimal("1") + offset_pct)
    else:  # match
        price = avg_price

    return max(price, floor_price).quantize(Decimal("0.01"))


async def recalculate_listing_price(
    session: AsyncSession,
    listing_id,
    product_cost: Decimal,
    cost_currency: str,
    target_currency: str,
    pricing_strategy: str,
    pricing_config: dict,
    platform: str,
) -> Decimal | None:
    """Recalculate price for a single listing based on its strategy.

    Returns new price or None if no change needed.
    """
    exchange_rate = await get_exchange_rate(session, cost_currency, target_currency)

    if pricing_strategy == "fixed":
        return None  # Fixed prices don't change

    elif pricing_strategy == "cost_plus":
        margin = Decimal(str(pricing_config.get("margin_pct", "0.30")))
        shipping = Decimal(str(pricing_config.get("shipping_estimate", "0")))
        return calculate_cost_plus_price(
            product_cost, cost_currency, target_currency, exchange_rate, margin, platform, shipping
        )

    elif pricing_strategy == "competitor_match":
        competitors = [Decimal(str(p)) for p in pricing_config.get("competitor_prices", [])]
        floor = Decimal(str(pricing_config.get("min_price", "0")))
        position = pricing_config.get("position", "below")
        return calculate_competitor_match_price(competitors, position, floor_price=floor)

    elif pricing_strategy == "ai_dynamic":
        # Phase 4: will call AI pricing optimizer agent
        margin = Decimal(str(pricing_config.get("margin_pct", "0.25")))
        shipping = Decimal(str(pricing_config.get("shipping_estimate", "0")))
        return calculate_cost_plus_price(
            product_cost, cost_currency, target_currency, exchange_rate, margin, platform, shipping
        )

    return None


async def record_price_change(
    session: AsyncSession,
    listing_id,
    old_price: Decimal,
    new_price: Decimal,
    currency: str,
    reason: str,
) -> None:
    """Record a price change in the price history."""
    history = PriceHistory(
        listing_id=listing_id,
        old_price=old_price,
        new_price=new_price,
        currency=currency,
        reason=reason,
    )
    session.add(history)
    await session.flush()


async def fetch_exchange_rates_from_api() -> dict[str, dict[str, float]]:
    """Fetch exchange rates from a free API. Called by Celery beat task."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://api.exchangerate.host/latest",
            params={"base": "CNY", "symbols": "AUD,USD,GBP,EUR"},
        )
        if resp.status_code == 200:
            data = resp.json()
            return {"CNY": data.get("rates", {})}

        # Fallback hardcoded rates (approximate)
        return {
            "CNY": {"AUD": 0.22, "USD": 0.14, "GBP": 0.11, "EUR": 0.13}
        }
