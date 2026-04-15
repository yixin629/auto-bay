import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class LineItemCreate(BaseModel):
    listing_id: uuid.UUID | None = None
    product_id: uuid.UUID | None = None
    sku: str | None = None
    title: str
    quantity: int = 1
    unit_price: Decimal = Decimal("0")


class OrderCreate(BaseModel):
    platform_connection_id: uuid.UUID | None = None
    external_order_id: str | None = None
    customer_name: str | None = None
    customer_email: str | None = None
    shipping_address: dict = Field(default_factory=dict)
    billing_address: dict = Field(default_factory=dict)
    currency: str = "AUD"
    line_items: list[LineItemCreate] = Field(default_factory=list)
    notes: str | None = None
    ordered_at: datetime | None = None


class OrderUpdate(BaseModel):
    status: str | None = None
    payment_status: str | None = None
    notes: str | None = None
    shipped_at: datetime | None = None
    delivered_at: datetime | None = None
    tracking_number: str | None = None
    carrier: str | None = None


class LineItemResponse(BaseModel):
    id: uuid.UUID
    order_id: uuid.UUID
    listing_id: uuid.UUID | None
    product_id: uuid.UUID | None
    sku: str | None
    title: str
    quantity: int
    unit_price: Decimal
    total_price: Decimal

    model_config = {"from_attributes": True}


class ShipmentResponse(BaseModel):
    id: uuid.UUID
    order_id: uuid.UUID
    carrier: str | None
    tracking_number: str | None
    label_url: str | None
    status: str
    shipped_at: datetime | None
    estimated_delivery: datetime | None
    customs_info: dict

    model_config = {"from_attributes": True}


class OrderResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    platform_connection_id: uuid.UUID | None
    platform: str | None
    region: str | None
    external_order_id: str | None
    status: str
    customer_name: str | None
    customer_email: str | None
    shipping_address: dict
    billing_address: dict
    subtotal: Decimal
    shipping_cost: Decimal
    platform_fees: Decimal
    tax: Decimal
    total: Decimal
    currency: str
    payment_status: str
    notes: str | None
    ordered_at: datetime | None
    shipped_at: datetime | None
    delivered_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OrderDetailResponse(OrderResponse):
    line_items: list[LineItemResponse] = []
    shipments: list[ShipmentResponse] = []


class OrderListResponse(BaseModel):
    items: list[OrderResponse]
    total: int
