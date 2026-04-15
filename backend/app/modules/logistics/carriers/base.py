"""Abstract interface for logistics/carrier integrations."""

from decimal import Decimal
from typing import Protocol

from pydantic import BaseModel


class ShipmentRequest(BaseModel):
    from_address: dict
    to_address: dict
    weight_grams: int
    dimensions_cm: dict | None = None
    declared_value: Decimal = Decimal("0")
    currency: str = "AUD"
    service_type: str = "standard"  # standard, express, economy


class ShippingRate(BaseModel):
    carrier: str
    service: str
    rate: Decimal
    currency: str
    estimated_days: int
    tracking_available: bool = True


class ShipmentLabel(BaseModel):
    shipment_id: str
    tracking_number: str
    carrier: str
    label_url: str
    label_format: str = "PDF"
    customs_form_url: str | None = None


class TrackingEvent(BaseModel):
    timestamp: str
    status: str
    location: str | None = None
    description: str


class TrackingStatus(BaseModel):
    tracking_number: str
    carrier: str
    status: str  # in_transit, out_for_delivery, delivered, exception
    estimated_delivery: str | None = None
    events: list[TrackingEvent] = []


class LogisticsAdapter(Protocol):
    """Abstract interface for shipping/logistics providers."""

    async def get_rates(self, request: ShipmentRequest) -> list[ShippingRate]: ...
    async def create_shipment(self, request: ShipmentRequest) -> ShipmentLabel: ...
    async def track_shipment(self, tracking_number: str) -> TrackingStatus: ...
    async def cancel_shipment(self, shipment_id: str) -> bool: ...
