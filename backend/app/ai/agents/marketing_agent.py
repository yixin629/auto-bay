"""AI agent for marketing — ad copy, SEO keywords, social media content."""

import json
import logging

from app.ai.llm import ModelTier, llm_client

logger = logging.getLogger(__name__)


async def generate_ad_copy(
    product_title: str,
    product_description: str,
    platform: str,
    target_audience: str = "general",
) -> dict:
    """Generate ad copy variants for a specific platform."""
    platform_constraints = {
        "google_ads": "Headlines max 30 chars, descriptions max 90 chars. Generate 5 headlines + 3 descriptions.",
        "facebook_ads": "Primary text ~125 chars, headline ~40 chars. Generate 3 variants.",
        "tiktok_ads": "Short, punchy, emoji-friendly. Max 100 chars. Generate 3 variants.",
        "ebay_promoted": "Focus on value and free shipping. Generate 3 taglines.",
        "amazon_ppc": "Keyword-rich headlines. Generate 5 keyword-focused headlines.",
    }
    constraints = platform_constraints.get(platform, "Generate 3 ad copy variants.")

    system = f"""You are an expert performance marketer for cross-border e-commerce.
Platform: {platform}
Target audience: {target_audience}
{constraints}

Return JSON: {{
  "headlines": ["..."],
  "descriptions": ["..."],
  "call_to_action": "..."
}}"""

    messages = [
        {
            "role": "user",
            "content": f"Product: {product_title}\nDescription: {product_description}",
        }
    ]
    result = await llm_client.complete(
        messages, tier=ModelTier.STANDARD, system=system, max_tokens=400, temperature=0.7
    )

    try:
        parsed = json.loads(result.content)
        parsed["model"] = result.model
        parsed["tokens"] = result.input_tokens + result.output_tokens
        parsed["cost"] = result.cost_usd
        return parsed
    except json.JSONDecodeError:
        return {"headlines": [], "descriptions": [result.content], "call_to_action": ""}


async def generate_seo_keywords(
    product_title: str,
    category: str = "",
    market: str = "AU",
) -> dict:
    """Generate SEO keywords for product listings. Uses BUDGET model."""
    system = f"""You are an SEO specialist for e-commerce in the {market} market.
Generate relevant search keywords for this product.

Return JSON: {{
  "primary_keywords": ["..."],
  "long_tail_keywords": ["..."],
  "negative_keywords": ["..."]
}}"""

    messages = [
        {
            "role": "user",
            "content": f"Product: {product_title}\nCategory: {category}",
        }
    ]
    result = await llm_client.complete(
        messages, tier=ModelTier.BUDGET, system=system, max_tokens=200, temperature=0.3
    )

    try:
        return json.loads(result.content)
    except json.JSONDecodeError:
        return {"primary_keywords": [], "long_tail_keywords": [], "negative_keywords": []}


async def generate_social_post(
    product_title: str,
    product_description: str,
    platform: str = "instagram",
    tone: str = "casual",
) -> dict:
    """Generate social media post content."""
    system = f"""You are a social media content creator for an e-commerce brand.
Platform: {platform}, Tone: {tone}
Create an engaging post with relevant hashtags.

Return JSON: {{
  "caption": "...",
  "hashtags": ["..."],
  "call_to_action": "..."
}}"""

    messages = [
        {
            "role": "user",
            "content": f"Product: {product_title}\nDescription: {product_description}",
        }
    ]
    result = await llm_client.complete(
        messages, tier=ModelTier.BUDGET, system=system, max_tokens=300, temperature=0.8
    )

    try:
        return json.loads(result.content)
    except json.JSONDecodeError:
        return {"caption": result.content, "hashtags": [], "call_to_action": ""}
