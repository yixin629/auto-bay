"""Unified LLM gateway with tiered model routing.

BUDGET:   Fast/cheap for bulk ops (classification, titles)
STANDARD: Balanced for generation (descriptions, customer replies)
PREMIUM:  Best reasoning for complex analysis (trend synthesis)
"""

import enum
import logging
import time

import anthropic
import openai

from app.config import settings

logger = logging.getLogger(__name__)


class ModelTier(str, enum.Enum):
    BUDGET = "budget"
    STANDARD = "standard"
    PREMIUM = "premium"


# Model mapping — easily swappable
MODEL_MAP = {
    ModelTier.BUDGET: "claude-haiku-4-5-20251001",
    ModelTier.STANDARD: "claude-sonnet-4-6",
    ModelTier.PREMIUM: "claude-opus-4-6",
}

# Approximate cost per 1K tokens (input/output)
COST_PER_1K = {
    "claude-haiku-4-5-20251001": {"input": 0.001, "output": 0.005},
    "claude-sonnet-4-6": {"input": 0.003, "output": 0.015},
    "claude-opus-4-6": {"input": 0.015, "output": 0.075},
}


class LLMResponse:
    def __init__(self, content: str, model: str, input_tokens: int, output_tokens: int, latency_ms: float):
        self.content = content
        self.model = model
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.latency_ms = latency_ms

    @property
    def cost_usd(self) -> float:
        costs = COST_PER_1K.get(self.model, {"input": 0.01, "output": 0.03})
        return (self.input_tokens / 1000 * costs["input"]) + (
            self.output_tokens / 1000 * costs["output"]
        )


class LLMClient:
    def __init__(self):
        self._anthropic = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    async def complete(
        self,
        messages: list[dict],
        tier: ModelTier = ModelTier.STANDARD,
        system: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> LLMResponse:
        model = MODEL_MAP[tier]
        start = time.monotonic()

        kwargs = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if system:
            kwargs["system"] = system

        response = await self._anthropic.messages.create(**kwargs)

        latency = (time.monotonic() - start) * 1000
        content = response.content[0].text if response.content else ""

        result = LLMResponse(
            content=content,
            model=model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            latency_ms=latency,
        )
        logger.info(
            "LLM call: model=%s tokens=%d/%d cost=$%.4f latency=%.0fms",
            model,
            result.input_tokens,
            result.output_tokens,
            result.cost_usd,
            result.latency_ms,
        )
        return result


# Singleton
llm_client = LLMClient()
