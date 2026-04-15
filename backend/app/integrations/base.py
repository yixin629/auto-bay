"""Abstract interfaces for all external platform integrations.

Every marketplace, logistics provider, and sourcing platform must implement
the relevant protocol so business logic never depends on platform specifics.
"""

from datetime import datetime
from decimal import Decimal
from typing import Protocol, runtime_checkable

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Shared DTOs
# ---------------------------------------------------------------------------


class ListingCreateDTO(BaseModel):
    internal_product_id: str
    title: str
    description: str
    description_html: str | None = None
    images: list[dict] = []
    category_id: str | None = None
    price: Decimal
    currency: str
    quantity: int
    attributes: dict = {}
    weight_grams: int | None = None
    dimensions_cm: dict | None = None
    condition: str = "new"


class ListingUpdateDTO(BaseModel):
    title: str | None = None
    description: str | None = None
    price: Decimal | None = None
    quantity: int | None = None
    attributes: dict | None = None


class ExternalListingResult(BaseModel):
    external_id: str
    external_url: str | None = None
    status: str = "active"
    raw_response: dict = {}


class ExternalOrderData(BaseModel):
    external_order_id: str
    status: str
    customer_name: str | None = None
    customer_email: str | None = None
    shipping_address: dict = {}
    line_items: list[dict] = []
    subtotal: Decimal = Decimal("0")
    shipping_cost: Decimal = Decimal("0")
    platform_fees: Decimal = Decimal("0")
    tax: Decimal = Decimal("0")
    total: Decimal = Decimal("0")
    currency: str = "AUD"
    ordered_at: datetime | None = None


class TrackingInfo(BaseModel):
    carrier: str
    tracking_number: str
    shipped_at: datetime | None = None


class ExternalMessageData(BaseModel):
    external_thread_id: str
    sender: str
    body: str
    received_at: datetime


# ---------------------------------------------------------------------------
# Marketplace Connector Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class MarketplaceConnector(Protocol):
    """Uniform interface all marketplace integrations must implement."""

    # --- Listings ---
    async def create_listing(self, data: ListingCreateDTO) -> ExternalListingResult: ...

    async def update_listing(
        self, external_id: str, data: ListingUpdateDTO
    ) -> ExternalListingResult: ...

    async def delete_listing(self, external_id: str) -> bool: ...

    # --- Inventory / Price ---
    async def update_stock(self, external_id: str, quantity: int) -> bool: ...

    async def update_price(
        self, external_id: str, price: Decimal, currency: str
    ) -> bool: ...

    # --- Orders ---
    async def fetch_orders(
        self, since: datetime, status: str | None = None
    ) -> list[ExternalOrderData]: ...

    async def ship_order(
        self, external_order_id: str, tracking: TrackingInfo
    ) -> bool: ...

    async def refund_order(
        self, external_order_id: str, amount: Decimal, reason: str
    ) -> bool: ...

    # --- Messages ---
    async def fetch_messages(self, since: datetime) -> list[ExternalMessageData]: ...

    async def send_message(self, thread_id: str, body: str) -> bool: ...

    # --- Auth ---
    async def refresh_credentials(self) -> dict: ...

    async def validate_connection(self) -> bool: ...
