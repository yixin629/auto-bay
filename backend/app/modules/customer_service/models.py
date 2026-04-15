import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin
from app.modules.products.models import Platform


class MessageDirection(str, enum.Enum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class MessageIntent(str, enum.Enum):
    SHIPPING_STATUS = "shipping_status"
    RETURN_REQUEST = "return_request"
    PRODUCT_QUESTION = "product_question"
    COMPLAINT = "complaint"
    GENERAL = "general"
    UNKNOWN = "unknown"


class CustomerMessage(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "customer_messages"

    order_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id"), nullable=True, index=True
    )
    platform_connection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("platform_connections.id"), nullable=False
    )
    platform: Mapped[Platform] = mapped_column(Enum(Platform), nullable=False)
    external_thread_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    direction: Mapped[MessageDirection] = mapped_column(Enum(MessageDirection), nullable=False)
    sender: Mapped[str | None] = mapped_column(String(255), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    intent: Mapped[MessageIntent] = mapped_column(
        Enum(MessageIntent), default=MessageIntent.UNKNOWN, server_default="unknown"
    )
    is_ai_generated: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    ai_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    requires_human: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    ai_draft_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
