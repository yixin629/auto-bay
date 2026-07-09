"""AI agent for customer service — intent classification + response generation."""

import json
import logging

from app.ai.llm import ModelTier, llm_client
from app.ai.prompts.loader import render_prompt

logger = logging.getLogger(__name__)


async def classify_intent(message: str) -> dict:
    """Classify customer message intent. Uses BUDGET model for speed."""
    system = render_prompt("customer_service/intent_classifier.system.txt")

    messages = [{"role": "user", "content": f"Customer message: {message}"}]
    result = await llm_client.complete(messages, tier=ModelTier.BUDGET, system=system, max_tokens=50, temperature=0.1)

    try:
        return json.loads(result.content)
    except json.JSONDecodeError:
        return {"intent": "unknown", "confidence": 0.0}


async def generate_response(
    customer_message: str,
    intent: str,
    order_context: dict | None = None,
) -> dict:
    """Generate a helpful response to the customer. Uses STANDARD model."""
    context_info = ""
    if order_context:
        context_info = f"""
Order Context:
- Order ID: {order_context.get('order_id', 'N/A')}
- Status: {order_context.get('status', 'N/A')}
- Tracking: {order_context.get('tracking_number', 'N/A')}
- Items: {order_context.get('items', 'N/A')}
"""

    system = render_prompt(
        "customer_service/response_generator.system.txt",
        intent=intent,
        context_info=context_info,
    )

    messages = [{"role": "user", "content": f"Customer message: {customer_message}"}]
    result = await llm_client.complete(messages, tier=ModelTier.STANDARD, system=system, max_tokens=300, temperature=0.5)

    try:
        return json.loads(result.content)
    except json.JSONDecodeError:
        return {"response": result.content, "suggested_actions": []}
