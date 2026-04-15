import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class ListingCreate(BaseModel):
    product_id: uuid.UUID
    platform_connection_id: uuid.UUID
    title: str | None = None
    price: Decimal | None = Field(default=None, ge=0)
    currency: str = "AUD"
    pricing_strategy: str = "fixed"
    pricing_config: dict = Field(default_factory=dict)


class ListingUpdate(BaseModel):
    title: str | None = None
    price: Decimal | None = Field(default=None, ge=0)
    currency: str | None = None
    status: str | None = None
    external_listing_id: str | None = None
    external_url: str | None = None
    platform_category_id: str | None = None
    platform_specific: dict | None = None
    pricing_strategy: str | None = None
    pricing_config: dict | None = None
    error_message: str | None = None


class ListingResponse(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    platform_connection_id: uuid.UUID
    platform: str
    region: str
    external_listing_id: str | None
    external_url: str | None
    status: str
    title: str | None
    price: Decimal | None
    currency: str
    platform_category_id: str | None
    platform_specific: dict
    pricing_strategy: str
    pricing_config: dict
    last_synced_at: datetime | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ListingListResponse(BaseModel):
    items: list[ListingResponse]
    total: int
