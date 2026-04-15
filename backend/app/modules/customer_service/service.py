"""Customer service module — AI-powered message handling with human escalation."""

import logging
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.agents.customer_support import classify_intent, generate_response
from app.modules.customer_service.models import (
    CustomerMessage,
    MessageDirection,
    MessageIntent,
)

logger = logging.getLogger(__name__)

# Confidence threshold: auto-send if above, flag for human if below
AUTO_SEND_THRESHOLD = 0.85


async def handle_inbound_message(
    session: AsyncSession,
    platform_connection_id: uuid.UUID,
    platform: str,
    external_thread_id: str,
    sender: str,
    body: str,
    order_id: uuid.UUID | None = None,
) -> CustomerMessage:
    """Process an inbound customer message through the AI pipeline.

    1. Save the inbound message
    2. Classify intent (BUDGET model)
    3. Generate response (STANDARD model)
    4. Check confidence → auto-send or flag for human
    """
    # Save inbound message
    message = CustomerMessage(
        platform_connection_id=platform_connection_id,
        platform=platform,
        external_thread_id=external_thread_id,
        direction=MessageDirection.INBOUND,
        sender=sender,
        body=body,
        order_id=order_id,
    )
    session.add(message)
    await session.flush()

    # Classify intent
    try:
        intent_result = await classify_intent(body)
        message.intent = MessageIntent(intent_result.get("intent", "unknown"))
        confidence = intent_result.get("confidence", 0.0)
    except Exception as e:
        logger.error("Intent classification failed: %s", e)
        message.intent = MessageIntent.UNKNOWN
        confidence = 0.0

    # Generate AI response
    try:
        response_result = await generate_response(
            customer_message=body,
            intent=message.intent.value,
            order_context={},  # TODO: fetch order details if order_id is set
        )
        message.ai_draft_response = response_result.get("response", "")
        message.ai_confidence = confidence
    except Exception as e:
        logger.error("Response generation failed: %s", e)
        message.ai_draft_response = None
        message.ai_confidence = 0.0

    # Decide: auto-send or flag for human
    if message.ai_confidence and message.ai_confidence >= AUTO_SEND_THRESHOLD:
        message.requires_human = False
        message.is_ai_generated = True
        # TODO: call connector.send_message() to auto-send
        logger.info("Auto-sending AI response (confidence: %.2f)", message.ai_confidence)
    else:
        message.requires_human = True
        logger.info("Flagging for human review (confidence: %.2f)", message.ai_confidence or 0)

    await session.flush()
    return message


async def list_messages(
    session: AsyncSession,
    user_id: uuid.UUID,
    requires_human: bool | None = None,
    offset: int = 0,
    limit: int = 50,
) -> tuple[list[CustomerMessage], int]:
    """List customer messages, optionally filtered by human review needed."""
    from app.modules.products.models import PlatformConnection

    query = (
        select(CustomerMessage)
        .join(PlatformConnection, CustomerMessage.platform_connection_id == PlatformConnection.id)
        .where(PlatformConnection.user_id == user_id)
    )
    count_query = (
        select(func.count())
        .select_from(CustomerMessage)
        .join(PlatformConnection, CustomerMessage.platform_connection_id == PlatformConnection.id)
        .where(PlatformConnection.user_id == user_id)
    )

    if requires_human is not None:
        query = query.where(CustomerMessage.requires_human == requires_human)
        count_query = count_query.where(CustomerMessage.requires_human == requires_human)

    query = query.order_by(CustomerMessage.created_at.desc()).offset(offset).limit(limit)
    result = await session.execute(query)
    total = (await session.execute(count_query)).scalar_one()
    return list(result.scalars().all()), total


async def approve_and_send(
    session: AsyncSession, message_id: uuid.UUID, response_text: str | None = None
) -> CustomerMessage:
    """Approve an AI draft (optionally edited) and send it."""
    message = await session.get(CustomerMessage, message_id)
    if not message:
        from app.core.exceptions import NotFoundError
        raise NotFoundError("Message not found")

    final_text = response_text or message.ai_draft_response
    if not final_text:
        from app.core.exceptions import BadRequestError
        raise BadRequestError("No response text provided")

    # Create the outbound message
    outbound = CustomerMessage(
        platform_connection_id=message.platform_connection_id,
        platform=message.platform,
        external_thread_id=message.external_thread_id,
        direction=MessageDirection.OUTBOUND,
        sender="AutoBay",
        body=final_text,
        order_id=message.order_id,
        is_ai_generated=True,
        intent=message.intent,
    )
    session.add(outbound)

    message.requires_human = False
    await session.flush()

    # TODO: call connector.send_message() to actually send
    logger.info("Sent response for thread %s", message.external_thread_id)
    return outbound
