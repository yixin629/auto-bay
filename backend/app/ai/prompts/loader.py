"""Prompt template loading utilities."""

from functools import lru_cache
from pathlib import Path
from string import Template

PROMPTS_DIR = Path(__file__).resolve().parent


@lru_cache(maxsize=64)
def load_prompt(relative_path: str) -> str:
    """Load and cache a prompt template from the prompts directory."""
    return (PROMPTS_DIR / relative_path).read_text(encoding="utf-8")


def render_prompt(relative_path: str, **context: str) -> str:
    """Render a prompt template using Template variables."""
    normalized_context = {k: "" if v is None else str(v) for k, v in context.items()}
    return Template(load_prompt(relative_path)).safe_substitute(**normalized_context)
