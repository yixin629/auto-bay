import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class SourcingMode(str, enum.Enum):
    ALIBABA_1688 = "alibaba_1688"
    ALIBABA_INTL = "alibaba_intl"
    DOMESTIC_AGENCY = "domestic_agency"
    DROPSHIP = "dropship"
    OWN_INVENTORY = "own_inventory"


class ProductStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class Platform(str, enum.Enum):
    EBAY = "ebay"
    AMAZON = "amazon"
    SHOPIFY = "shopify"
    TIKTOK = "tiktok"
    HARVEY_NORMAN = "harvey_norman"


# ---------------------------------------------------------------------------
# Product
# ---------------------------------------------------------------------------


class Product(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "products"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )

    sku: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    description_html: Mapped[str | None] = mapped_column(Text, nullable=True)

    category: Mapped[str | None] = mapped_column(String(255), nullable=True)
    brand: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Structured JSON fields
    images: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")
    attributes: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")

    # Physical properties
    weight_grams: Mapped[int | None] = mapped_column(Integer, nullable=True)
    dimensions_cm: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Customs / trade compliance
    hs_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    country_of_origin: Mapped[str | None] = mapped_column(String(2), nullable=True)

    # Sourcing
    sourcing_mode: Mapped[SourcingMode] = mapped_column(Enum(SourcingMode), nullable=False)
    sourcing_config: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")

    # Costing
    base_cost: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    base_cost_currency: Mapped[str] = mapped_column(
        String(3), default="CNY", server_default="CNY"
    )

    # Status
    status: Mapped[ProductStatus] = mapped_column(
        Enum(ProductStatus), default=ProductStatus.DRAFT, server_default="draft"
    )

    # AI-generated metadata (embeddings, tags, classification scores, etc.)
    ai_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")

    # Relationships
    translations: Mapped[list["ProductTranslation"]] = relationship(
        "ProductTranslation", back_populates="product", cascade="all, delete-orphan"
    )


# ---------------------------------------------------------------------------
# Product Translation
# ---------------------------------------------------------------------------


class ProductTranslation(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "product_translations"
    __table_args__ = (
        UniqueConstraint("product_id", "locale", name="uq_product_translation_locale"),
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id"), nullable=False, index=True
    )
    locale: Mapped[str] = mapped_column(String(10), nullable=False)

    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    description_html: Mapped[str | None] = mapped_column(Text, nullable=True)

    seo_keywords: Mapped[list[str]] = mapped_column(
        ARRAY(String), default=list, server_default="{}"
    )
    is_ai_generated: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )

    # Relationships
    product: Mapped["Product"] = relationship("Product", back_populates="translations")


# ---------------------------------------------------------------------------
# Platform Connection
# ---------------------------------------------------------------------------


class PlatformConnection(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "platform_connections"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "platform", "region", name="uq_platform_connection_user_platform_region"
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    platform: Mapped[Platform] = mapped_column(Enum(Platform), nullable=False)
    region: Mapped[str] = mapped_column(String(5), nullable=False)
    account_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Encrypted OAuth tokens, refresh tokens, API keys, etc.
    credentials: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    last_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
