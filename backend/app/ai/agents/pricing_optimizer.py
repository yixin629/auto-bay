"""AI agent for pricing optimization — uses rules + LLM for anomaly explanation."""

import json
import logging
from decimal import Decimal

from app.ai.llm import ModelTier, llm_client

logger = logging.getLogger(__name__)


async def explain_pricing_recommendation(
    product_title: str,
    current_price: Decimal,
    recommended_price: Decimal,
    cost: Decimal,
    competitor_prices: list[Decimal],
    market: str,
) -> str:
    """Generate human-readable explanation for a pricing recommendation.

    The price calculation itself is done by the rule engine in pricing/service.py.
    This function only generates the explanation using a BUDGET model.
    """
    system = """You are a pricing analyst. Explain this pricing recommendation
in 2-3 concise sentences. Reference cost, margin, and competition data."""

    avg_competitor = sum(competitor_prices) / len(competitor_prices) if competitor_prices else Decimal("0")

    messages = [
        {
            "role": "user",
            "content": f"""Product: {product_title}
Market: {market}
Cost: {cost}
Current price: {current_price}
Recommended price: {recommended_price}
Average competitor price: {avg_competitor}
Number of competitors: {len(competitor_prices)}

Explain why this price is recommended.""",
        }
    ]

    result = await llm_client.complete(
        messages, tier=ModelTier.BUDGET, system=system, max_tokens=150, temperature=0.3
    )
    return result.content


async def detect_pricing_anomalies(
    listings: list[dict],
) -> list[dict]:
    """Detect pricing anomalies across listings using rule-based logic.

    Returns listings that are priced significantly above or below market.
    No LLM needed — pure math.
    """
    anomalies = []
    for listing in listings:
        price = Decimal(str(listing.get("price", 0)))
        cost = Decimal(str(listing.get("cost", 0)))
        competitor_avg = Decimal(str(listing.get("competitor_avg", 0)))

        if cost > 0:
            margin = (price - cost) / price if price > 0 else Decimal("0")
            if margin < Decimal("0.10"):
                anomalies.append({
                    **listing,
                    "issue": "low_margin",
                    "detail": f"Margin is only {margin:.0%}",
                })
            elif margin > Decimal("0.80"):
                anomalies.append({
                    **listing,
                    "issue": "high_margin",
                    "detail": f"Margin is {margin:.0%} — may be overpriced",
                })

        if competitor_avg > 0 and price > 0:
            ratio = price / competitor_avg
            if ratio > Decimal("1.5"):
                anomalies.append({
                    **listing,
                    "issue": "above_market",
                    "detail": f"Price is {ratio:.0%} of market average",
                })
            elif ratio < Decimal("0.5"):
                anomalies.append({
                    **listing,
                    "issue": "below_market",
                    "detail": f"Price is only {ratio:.0%} of market average",
                })

    return anomalies
