"""AI agent for generating product listings — titles, descriptions, translations."""

import logging

from app.ai.llm import LLMResponse, ModelTier, llm_client

logger = logging.getLogger(__name__)


async def generate_listing_title(
    product_title: str,
    category: str | None,
    attributes: dict,
    platform: str,
    region: str,
) -> LLMResponse:
    """Generate an SEO-optimized listing title for a specific platform."""
    system = f"""You are an expert {platform} listing title optimizer for the {region} market.
Generate a title that:
- Is under 80 characters for eBay, 200 for Amazon, 255 for Shopify
- Front-loads the most searchable keywords
- Includes brand, key specs, and condition
- Never uses ALL CAPS or excessive punctuation
- Is in English
Return ONLY the title, nothing else."""

    messages = [
        {
            "role": "user",
            "content": f"Product: {product_title}\nCategory: {category or 'General'}\nAttributes: {attributes}\n\nGenerate the best listing title.",
        }
    ]
    return await llm_client.complete(messages, tier=ModelTier.BUDGET, system=system, max_tokens=100, temperature=0.3)


async def generate_listing_description(
    product_title: str,
    description: str | None,
    attributes: dict,
    platform: str,
    region: str,
    language: str = "en",
) -> LLMResponse:
    """Generate a compelling product description for a specific platform and language."""
    lang_instruction = "Write in English." if language == "en" else f"Write in {language}."

    system = f"""You are an expert e-commerce copywriter for {platform} ({region} market).
{lang_instruction}
Generate a compelling product description that:
- Highlights key features and benefits
- Uses bullet points for scanability
- Includes relevant SEO keywords naturally
- Addresses common buyer concerns
- Is professional and trustworthy
- Appropriate length: ~150-300 words

Return the description in HTML format with proper tags."""

    messages = [
        {
            "role": "user",
            "content": f"Product: {product_title}\nExisting Description: {description or 'None'}\nAttributes: {attributes}\n\nGenerate the product description.",
        }
    ]
    return await llm_client.complete(messages, tier=ModelTier.STANDARD, system=system, max_tokens=800, temperature=0.6)


async def translate_listing(
    title: str,
    description: str,
    target_language: str,
) -> LLMResponse:
    """Translate listing content to a target language while preserving SEO quality."""
    system = f"""You are a professional e-commerce translator.
Translate the following listing content to {target_language}.
Preserve SEO keywords, maintain marketing tone, adapt cultural references.
Return JSON: {{"title": "...", "description": "..."}}"""

    messages = [
        {
            "role": "user",
            "content": f"Title: {title}\n\nDescription:\n{description}",
        }
    ]
    return await llm_client.complete(messages, tier=ModelTier.STANDARD, system=system, max_tokens=1000, temperature=0.4)
