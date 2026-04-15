import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


class LocationType(str, enum.Enum):
    OWN_WAREHOUSE = "own_warehouse"
    THIRD_PARTY_LOGISTICS = "third_party_logistics"
    SUPPLIER = "supplier"
    VIRTUAL = "virtual"


class MovementType(str, enum.Enum):
    PURCHASE = "purchase"
    SALE = "sale"
    ADJUSTMENT = "adjustment"
    RETURN_STOCK = "return_stock"
    TRANSFER = "transfer"


class InventoryLocation(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "inventory_locations"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    country: Mapped[str | None] = mapped_column(String(2), nullable=True)
    address: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    location_type: Mapped[LocationType] = mapped_column(
        Enum(LocationType), default=LocationType.OWN_WAREHOUSE, server_default="own_warehouse"
    )


class InventoryItem(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "inventory_items"
    __table_args__ = (
        UniqueConstraint("product_id", "location_id", name="uq_inventory_product_location"),
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id"), nullable=False, index=True
    )
    location_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("inventory_locations.id"), nullable=False, index=True
    )
    quantity_on_hand: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    quantity_reserved: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    reorder_point: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    reorder_quantity: Mapped[int] = mapped_column(Integer, default=0, server_default="0")


class InventoryMovement(UUIDMixin, Base):
    __tablename__ = "inventory_movements"

    inventory_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("inventory_items.id"), nullable=False, index=True
    )
    movement_type: Mapped[MovementType] = mapped_column(Enum(MovementType), nullable=False)
    quantity_change: Mapped[int] = mapped_column(Integer, nullable=False)
    reference_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    reference_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )
