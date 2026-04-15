"""AI agent for product research — trend analysis and profit scoring."""

import json
import logging
from decimal import Decimal

from app.ai.llm import ModelTier, llm_client

logger = logging.getLogger(__name__)


def calculate_profit_score(
    unit_cost_cny: Decimal,
    estimated_sale_price: Decimal,
    exchange_rate: Decimal,
    shipping_estimate: Decimal,
    platform_fee_pct: Decimal,
    demand_signal: float,      # 0-1 normalized
    competition_count: float,  # 0-1 normalized (lower = better)
    trend_velocity: float,     # 0-1 normalized
    supplier_reliability: float,  # 0-1 normalized
) -> float:
    """Deterministic profit scoring — NO LLM needed.

    Returns a score from 0.0 to 1.0 indicating product opportunity quality.
    """
    cost_in_target = unit_cost_cny * exchange_rate
    platform_fees = estimated_sale_price * platform_fee_pct
    gross_margin = estimated_sale_price - cost_in_target - shipping_estimate - platform_fees

    if estimated_sale_price > 0:
        margin_pct = float(gross_margin / estimated_sale_price)
    else:
        margin_pct = 0.0

    # Weighted score
    score = (
        max(0, min(1, margin_pct)) * 0.30
        + demand_signal * 0.25
        + (1 - competition_count) * 0.20
        + trend_velocity * 0.15
        + supplier_reliability * 0.10
    )
    return round(max(0.0, min(1.0, score)), 3)


async def analyze_product_opportunity(
    product_title: str,
    category: str,
    cost_cny: float,
    estimated_price: float,
    target_market: str,
    competitor_count: int = 0,
    monthly_searches: int = 0,
) -> dict:
    """Use AI to synthesize a human-readable product opportunity analysis.

    The numerical scoring is done by calculate_profit_score() above.
    This function uses PREMIUM tier LLM only for the qualitative synthesis.
    """
    system = """You are a cross-border e-commerce product analyst specializing in
CN→AU/US/UK markets. Analyze this product opportunity and provide:
1. Market viability assessment (1-2 sentences)
2. Key risks (bullet points)
3. Recommended selling strategy
4. Suggested improvements or bundling ideas

Return JSON: {
  "viability": "...",
  "risks": ["..."],
  "strategy": "...",
  "suggestions": ["..."],
  "recommended_platforms": ["ebay", "amazon", ...]
}"""

    messages = [
        {
            "role": "user",
            "content": f"""Product: {product_title}
Category: {category}
Cost (CNY): {cost_cny}
Estimated selling price: {estimated_price}
Target market: {target_market}
Competitor count: {competitor_count}
Monthly search volume: {monthly_searches}

Analyze this product opportunity.""",
        }
    ]

    result = await llm_client.complete(
        messages, tier=ModelTier.PREMIUM, system=system, max_tokens=500, temperature=0.4
    )

    try:
        return json.loads(result.content)
    except json.JSONDecodeError:
        return {"viability": result.content, "risks": [], "strategy": "", "suggestions": []}
