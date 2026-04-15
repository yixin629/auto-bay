"""Abstract interface for sourcing platform adapters."""

from decimal import Decimal
from typing import Protocol

from pydantic import BaseModel


class SourceProduct(BaseModel):
    source_id: str
    title: str
    title_en: str | None = None
    description: str | None = None
    images: list[str] = []
    price_min: Decimal = Decimal("0")
    price_max: Decimal = Decimal("0")
    currency: str = "CNY"
    moq: int = 1
    supplier_name: str | None = None
    supplier_id: str | None = None
    supplier_url: str | None = None
    product_url: str | None = None
    category: str | None = None
    attributes: dict = {}
    sales_count: int = 0
    rating: float = 0.0


class SourceProductDetail(SourceProduct):
    description_html: str | None = None
    sku_options: list[dict] = []
    shipping_templates: list[dict] = []
    supplier_rating: float = 0.0
    supplier_years: int = 0


class SourcingFilters(BaseModel):
    min_price: Decimal | None = None
    max_price: Decimal | None = None
    min_moq: int | None = None
    max_moq: int | None = None
    sort_by: str = "default"  # default, price_asc, price_desc, sales, rating
    page: int = 1
    page_size: int = 50


class SourcingAdapter(Protocol):
    """Abstract interface for product sourcing platforms."""

    async def search_products(
        self, query: str, filters: SourcingFilters | None = None
    ) -> list[SourceProduct]: ...

    async def get_product_detail(self, product_id: str) -> SourceProductDetail: ...

    async def get_shipping_estimate(
        self, product_id: str, destination_country: str, quantity: int
    ) -> Decimal: ...
