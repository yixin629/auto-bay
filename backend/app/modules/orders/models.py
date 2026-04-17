import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin
from app.modules.products.models import Platform


class OrderStatus(str, enum.Enum):
    NEW = "new"
    PROCESSING = "processing"
    AWAITING_SHIPMENT = "awaiting_shipment"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    RETURN_REQUESTED = "return_requested"
    RETURNED = "returned"
    REFUNDED = "refunded"


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    REFUNDED = "refunded"
    PARTIAL_REFUND = "partial_refund"


class ShipmentStatus(str, enum.Enum):
    LABEL_CREATED = "label_created"
    IN_TRANSIT = "in_transit"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    EXCEPTION = "exception"


class Order(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "orders"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    platform_connection_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("platform_connections.id"), nullable=True
    )
    platform: Mapped[Platform | None] = mapped_column(Enum(Platform), nullable=True)
    region: Mapped[str | None] = mapped_column(String(5), nullable=True)
    external_order_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus), default=OrderStatus.NEW, server_default="NEW"
    )
    customer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    customer_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    shipping_address: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    billing_address: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    subtotal: Mapped[float] = mapped_column(Numeric(12, 2), default=0, server_default="0")
    shipping_cost: Mapped[float] = mapped_column(Numeric(12, 2), default=0, server_default="0")
    platform_fees: Mapped[float] = mapped_column(Numeric(12, 2), default=0, server_default="0")
    tax: Mapped[float] = mapped_column(Numeric(12, 2), default=0, server_default="0")
    total: Mapped[float] = mapped_column(Numeric(12, 2), default=0, server_default="0")
    currency: Mapped[str] = mapped_column(String(3), default="AUD", server_default="AUD")
    payment_status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus), default=PaymentStatus.PENDING, server_default="PENDING"
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    ordered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    shipped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    line_items: Mapped[list["OrderLineItem"]] = relationship(
        "OrderLineItem", back_populates="order", cascade="all, delete-orphan"
    )
    shipments: Mapped[list["Shipment"]] = relationship(
        "Shipment", back_populates="order", cascade="all, delete-orphan"
    )


class OrderLineItem(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "order_line_items"

    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    listing_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("listings.id"), nullable=True
    )
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id"), nullable=True
    )
    sku: Mapped[str | None] = mapped_column(String(100), nullable=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    unit_price: Mapped[float] = mapped_column(Numeric(12, 2), default=0, server_default="0")
    total_price: Mapped[float] = mapped_column(Numeric(12, 2), default=0, server_default="0")

    order: Mapped["Order"] = relationship("Order", back_populates="line_items")


class Shipment(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "shipments"

    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    carrier: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tracking_number: Mapped[str | None] = mapped_column(String(255), nullable=True)
    label_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    status: Mapped[ShipmentStatus] = mapped_column(
        Enum(ShipmentStatus), default=ShipmentStatus.LABEL_CREATED, server_default="LABEL_CREATED"
    )
    shipped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    estimated_delivery: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    customs_info: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")

    order: Mapped["Order"] = relationship("Order", back_populates="shipments")
