import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin
from app.modules.products.models import Platform


class ListingStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING = "pending"
    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"
    ENDED = "ended"


class PricingStrategy(str, enum.Enum):
    FIXED = "fixed"
    COST_PLUS = "cost_plus"
    COMPETITOR_MATCH = "competitor_match"
    AI_DYNAMIC = "ai_dynamic"


class Listing(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "listings"
    __table_args__ = (
        UniqueConstraint(
            "platform_connection_id", "external_listing_id",
            name="uq_listing_platform_external",
        ),
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id"), nullable=False, index=True
    )
    platform_connection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("platform_connections.id"), nullable=False, index=True
    )
    platform: Mapped[Platform] = mapped_column(Enum(Platform), nullable=False)
    region: Mapped[str] = mapped_column(String(5), nullable=False)
    external_listing_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    external_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    status: Mapped[ListingStatus] = mapped_column(
        Enum(ListingStatus), default=ListingStatus.DRAFT, server_default="DRAFT"
    )
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    price: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="AUD", server_default="AUD")
    platform_category_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    platform_specific: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    pricing_strategy: Mapped[PricingStrategy] = mapped_column(
        Enum(PricingStrategy), default=PricingStrategy.FIXED, server_default="FIXED"
    )
    pricing_config: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    last_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
