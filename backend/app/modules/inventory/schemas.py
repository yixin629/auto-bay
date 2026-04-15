import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class LocationCreate(BaseModel):
    name: str
    country: str | None = None
    address: dict = Field(default_factory=dict)
    location_type: str = "own_warehouse"


class LocationResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    country: str | None
    address: dict
    location_type: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class InventoryItemResponse(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    location_id: uuid.UUID
    quantity_on_hand: int
    quantity_reserved: int
    quantity_available: int
    reorder_point: int
    reorder_quantity: int
    updated_at: datetime

    model_config = {"from_attributes": True}


class StockAdjustment(BaseModel):
    product_id: uuid.UUID
    location_id: uuid.UUID
    quantity_change: int
    movement_type: str = "adjustment"
    reference_type: str | None = None
    reference_id: uuid.UUID | None = None
    notes: str | None = None


class MovementResponse(BaseModel):
    id: uuid.UUID
    inventory_item_id: uuid.UUID
    movement_type: str
    quantity_change: int
    reference_type: str | None
    reference_id: uuid.UUID | None
    notes: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class InventoryListResponse(BaseModel):
    items: list[InventoryItemResponse]
    total: int
