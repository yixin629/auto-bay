"""AI agent for customer service — intent classification + response generation."""

import json
import logging

from app.ai.llm import ModelTier, llm_client

logger = logging.getLogger(__name__)


async def classify_intent(message: str) -> dict:
    """Classify customer message intent. Uses BUDGET model for speed."""
    system = """You are a customer service intent classifier for an e-commerce platform.
Classify the customer message into exactly one intent:
- shipping_status: asking about delivery, tracking, shipping time
- return_request: wants to return, exchange, or get refund
- product_question: asking about product specs, compatibility, features
- complaint: unhappy about quality, service, or experience
- general: greeting, thank you, other

Return JSON: {"intent": "...", "confidence": 0.0-1.0}"""

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

    system = f"""You are a friendly, professional customer service agent for an e-commerce store.
The customer's intent has been classified as: {intent}
{context_info}
Guidelines:
- Be empathetic and helpful
- If you have order info, reference specific details
- For shipping questions without tracking, say it will be provided soon
- For returns, outline the standard return process (14-day window)
- For complaints, apologize sincerely and offer resolution
- Keep responses concise (2-4 sentences)
- Never make up tracking numbers or order details you don't have
- Sign off with "Best regards, AutoBay Support"

Return JSON: {{"response": "your response text", "suggested_actions": ["list", "of", "follow-up actions"]}}"""

    messages = [{"role": "user", "content": f"Customer message: {customer_message}"}]
    result = await llm_client.complete(messages, tier=ModelTier.STANDARD, system=system, max_tokens=300, temperature=0.5)

    try:
        return json.loads(result.content)
    except json.JSONDecodeError:
        return {"response": result.content, "suggested_actions": []}
