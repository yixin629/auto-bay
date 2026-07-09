from pathlib import Path

import pytest

from app.ai.prompts.loader import PROMPTS_DIR, load_prompt, render_prompt


def test_load_prompt_reads_template_file() -> None:
    content = load_prompt("customer_service/intent_classifier.system.txt")

    assert "customer service intent classifier" in content
    assert '"intent"' in content


@pytest.mark.parametrize(
    ("template_path", "context", "expected_fragments"),
    [
        (
            "customer_service/response_generator.system.txt",
            {
                "intent": "shipping_status",
                "context_info": "Order Context:\n- Order ID: AU-123",
            },
            ["shipping_status", "Order ID: AU-123", "AutoBay Support"],
        ),
        (
            "listing_generation/title.system.txt",
            {"platform": "eBay", "region": "AU"},
            ["eBay listing title optimizer", "AU market", "Return ONLY the title"],
        ),
        (
            "listing_generation/description.system.txt",
            {
                "platform": "Amazon",
                "region": "US",
                "lang_instruction": "Write in English.",
            },
            ["Amazon", "US market", "Write in English."],
        ),
        (
            "listing_generation/translate.system.txt",
            {"target_language": "German"},
            ["German", '"title"', '"description"'],
        ),
        (
            "marketing/ad_copy.system.txt",
            {
                "platform": "facebook_ads",
                "target_audience": "pet owners",
                "constraints": "Generate 3 variants.",
            },
            ["facebook_ads", "pet owners", "Generate 3 variants."],
        ),
        (
            "marketing/seo_keywords.system.txt",
            {"market": "AU"},
            ["AU market", '"primary_keywords"', '"negative_keywords"'],
        ),
        (
            "marketing/social_post.system.txt",
            {"platform": "instagram", "tone": "casual"},
            ["Platform: instagram", "Tone: casual", '"hashtags"'],
        ),
    ],
)
def test_render_prompt_substitutes_expected_values(
    template_path: str,
    context: dict[str, str],
    expected_fragments: list[str],
) -> None:
    rendered = render_prompt(template_path, **context)

    for fragment in expected_fragments:
        assert fragment in rendered

    assert "$" not in rendered


def test_prompt_directories_match_expected_structure() -> None:
    prompt_files = {
        path.relative_to(PROMPTS_DIR).as_posix()
        for path in PROMPTS_DIR.rglob("*.txt")
    }

    assert prompt_files == {
        "customer_service/intent_classifier.system.txt",
        "customer_service/response_generator.system.txt",
        "listing_generation/description.system.txt",
        "listing_generation/title.system.txt",
        "listing_generation/translate.system.txt",
        "marketing/ad_copy.system.txt",
        "marketing/seo_keywords.system.txt",
        "marketing/social_post.system.txt",
    }