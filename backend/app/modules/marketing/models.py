import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


class CampaignType(str, enum.Enum):
    EBAY_PROMOTED = "ebay_promoted"
    AMAZON_PPC = "amazon_ppc"
    GOOGLE_ADS = "google_ads"
    FACEBOOK_ADS = "facebook_ads"
    TIKTOK_ADS = "tiktok_ads"
    SOCIAL_POST = "social_post"


class CampaignStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"


class MarketingCampaign(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "marketing_campaigns"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    campaign_type: Mapped[CampaignType] = mapped_column(Enum(CampaignType), nullable=False)
    status: Mapped[CampaignStatus] = mapped_column(
        Enum(CampaignStatus), default=CampaignStatus.DRAFT, server_default="draft"
    )
    budget_daily: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    budget_total: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="AUD", server_default="AUD")
    target_products: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")
    ad_copy: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    keywords: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")
    performance: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    is_ai_generated: Mapped[bool] = mapped_column(default=False)
    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AITask(UUIDMixin, Base):
    __tablename__ = "ai_tasks"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    task_type: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", server_default="pending")
    input_data: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    output_data: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    model_used: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tokens_used: Mapped[int | None] = mapped_column(nullable=True)
    cost_usd: Mapped[float | None] = mapped_column(Numeric(8, 4), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.utcnow(), server_default=func.now()
    )
