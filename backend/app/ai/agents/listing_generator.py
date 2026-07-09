"""AI agent for generating product listings — titles, descriptions, translations."""

import logging

from app.ai.llm import LLMResponse, ModelTier, llm_client
from app.ai.prompts.loader import render_prompt

logger = logging.getLogger(__name__)


async def generate_listing_title(
    product_title: str,
    category: str | None,
    attributes: dict,
    platform: str,
    region: str,
) -> LLMResponse:
    """Generate an SEO-optimized listing title for a specific platform."""
    system = render_prompt("listing_generation/title.system.txt", platform=platform, region=region)

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

    system = render_prompt(
        "listing_generation/description.system.txt",
        platform=platform,
        region=region,
        lang_instruction=lang_instruction,
    )

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
    system = render_prompt(
        "listing_generation/translate.system.txt",
        target_language=target_language,
    )

    messages = [
        {
            "role": "user",
            "content": f"Title: {title}\n\nDescription:\n{description}",
        }
    ]
    return await llm_client.complete(messages, tier=ModelTier.STANDARD, system=system, max_tokens=1000, temperature=0.4)
