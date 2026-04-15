import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.modules.products.models import ProductStatus, SourcingMode


# ---------------------------------------------------------------------------
# Nested value objects
# ---------------------------------------------------------------------------


class ImageItem(BaseModel):
    url: str
    position: int = 0
    alt_text: str = ""


class DimensionsCm(BaseModel):
    length: float
    width: float
    height: float


# ---------------------------------------------------------------------------
# Create / Update
# ---------------------------------------------------------------------------


class ProductCreate(BaseModel):
    sku: str = Field(..., min_length=1, max_length=100)
    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = None
    description_html: str | None = None
    category: str | None = Field(default=None, max_length=255)
    brand: str | None = Field(default=None, max_length=255)
    images: list[ImageItem] = Field(default_factory=list)
    attributes: dict = Field(default_factory=dict)
    weight_grams: int | None = None
    dimensions_cm: DimensionsCm | None = None
    hs_code: str | None = Field(default=None, max_length=20)
    country_of_origin: str | None = Field(default=None, min_length=2, max_length=2)
    sourcing_mode: SourcingMode
    sourcing_config: dict = Field(default_factory=dict)
    base_cost: Decimal | None = Field(default=None, ge=0)
    base_cost_currency: str = Field(default="CNY", min_length=3, max_length=3)
    status: ProductStatus = ProductStatus.DRAFT
    ai_metadata: dict = Field(default_factory=dict)


class ProductUpdate(BaseModel):
    sku: str | None = Field(default=None, min_length=1, max_length=100)
    title: str | None = Field(default=None, min_length=1, max_length=500)
    description: str | None = None
    description_html: str | None = None
    category: str | None = Field(default=None, max_length=255)
    brand: str | None = Field(default=None, max_length=255)
    images: list[ImageItem] | None = None
    attributes: dict | None = None
    weight_grams: int | None = None
    dimensions_cm: DimensionsCm | None = None
    hs_code: str | None = Field(default=None, max_length=20)
    country_of_origin: str | None = Field(default=None, min_length=2, max_length=2)
    sourcing_mode: SourcingMode | None = None
    sourcing_config: dict | None = None
    base_cost: Decimal | None = Field(default=None, ge=0)
    base_cost_currency: str | None = Field(default=None, min_length=3, max_length=3)
    status: ProductStatus | None = None
    ai_metadata: dict | None = None


# ---------------------------------------------------------------------------
# Response
# ---------------------------------------------------------------------------


class ProductResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    sku: str
    title: str
    description: str | None
    description_html: str | None
    category: str | None
    brand: str | None
    images: list
    attributes: dict
    weight_grams: int | None
    dimensions_cm: dict | None
    hs_code: str | None
    country_of_origin: str | None
    sourcing_mode: SourcingMode
    sourcing_config: dict
    base_cost: Decimal | None
    base_cost_currency: str
    status: ProductStatus
    ai_metadata: dict
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProductListResponse(BaseModel):
    items: list[ProductResponse]
    total: int
