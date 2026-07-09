import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.modules.products.models import Platform, ProductStatus, SourcingMode


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


# ---------------------------------------------------------------------------
# Platform Connections
# ---------------------------------------------------------------------------


class PlatformConnectionCreate(BaseModel):
    platform: Platform
    region: str = Field(..., min_length=2, max_length=5)
    account_name: str | None = Field(default=None, max_length=255)
    credentials: dict = Field(default_factory=dict)
    is_active: bool = True


class PlatformConnectionUpdate(BaseModel):
    account_name: str | None = Field(default=None, max_length=255)
    credentials: dict | None = None
    is_active: bool | None = None


class PlatformConnectionResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    platform: Platform
    region: str
    account_name: str | None
    has_credentials: bool
    credential_keys: list[str]
    is_active: bool
    last_synced_at: datetime | None
    last_sync_count: int
    last_sync_error: str | None
    alert_level: str
    alert_reason: str
    health_score: int
    stale_for_seconds: int | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PlatformConnectionListResponse(BaseModel):
    items: list[PlatformConnectionResponse]
    total: int


class PlatformConnectionTestResult(BaseModel):
    ok: bool
    platform: Platform
    region: str
    message: str


class PlatformOAuthStartRequest(BaseModel):
    platform: Platform
    region: str = Field(default="CN", min_length=2, max_length=5)
    scopes: list[str] = Field(default_factory=list)


class PlatformOAuthStartResponse(BaseModel):
    platform: Platform
    region: str
    authorization_url: str
    state: str


class PlatformOAuthCallbackResponse(BaseModel):
    ok: bool
    platform: Platform
    region: str
    message: str
    connection: PlatformConnectionResponse


class PlatformSyncEventResponse(BaseModel):
    id: uuid.UUID
    platform_connection_id: uuid.UUID
    user_id: uuid.UUID
    platform: Platform
    region: str
    event_type: str
    status: str
    message: str | None
    count: int
    duration_ms: int | None
    details: dict
    created_at: datetime

    model_config = {"from_attributes": True}


class PlatformSyncEventListResponse(BaseModel):
    items: list[PlatformSyncEventResponse]
    total: int


class PlatformSyncDailyTrendPoint(BaseModel):
    day: str
    total_events: int
    success_events: int
    error_events: int
    success_rate: float | None
    avg_duration_ms: float | None


class PlatformSyncMetricsResponse(BaseModel):
    platform_connection_id: uuid.UUID
    window_hours: int
    total_events: int
    success_events: int
    error_events: int
    success_rate: float | None
    avg_duration_ms: float | None
    consecutive_error_count: int
    last_success_at: datetime | None
    last_error_at: datetime | None
    daily_trend: list[PlatformSyncDailyTrendPoint] = Field(default_factory=list)
