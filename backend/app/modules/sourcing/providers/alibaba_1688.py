"""1688/Alibaba sourcing adapter.

1688.com does not have a clean public API for external developers.
Strategy:
1. Use Alibaba's cross-border sourcing API (if available via partnership)
2. Fallback to third-party data extraction services
3. Manual entry as last resort

This adapter provides the interface; actual scraping logic uses httpx.
"""

import logging
from decimal import Decimal

import httpx

from app.modules.sourcing.providers.base import (
    SourcingFilters,
    SourceProduct,
    SourceProductDetail,
)

logger = logging.getLogger(__name__)


class Alibaba1688Adapter:
    """1688.com sourcing adapter using third-party data extraction."""

    def __init__(self, api_key: str = ""):
        self._api_key = api_key
        self._client = httpx.AsyncClient(timeout=30.0)

    async def search_products(
        self, query: str, filters: SourcingFilters | None = None
    ) -> list[SourceProduct]:
        """Search 1688.com for products matching query."""
        filters = filters or SourcingFilters()

        # Using a third-party 1688 data API (e.g., DajiAPI, SerpApi, etc.)
        # Replace with actual API endpoint when configured
        try:
            resp = await self._client.get(
                "https://api.example.com/1688/search",
                params={
                    "keyword": query,
                    "page": filters.page,
                    "page_size": filters.page_size,
                    "sort": filters.sort_by,
                },
                headers={"Authorization": f"Bearer {self._api_key}"},
            )
            if resp.status_code != 200:
                logger.warning("1688 search failed: %s", resp.status_code)
                return []

            data = resp.json()
            products = []
            for item in data.get("items", []):
                products.append(
                    SourceProduct(
                        source_id=item.get("offer_id", ""),
                        title=item.get("subject", ""),
                        title_en=item.get("subject_en", ""),
                        images=[img.get("url", "") for img in item.get("images", [])],
                        price_min=Decimal(str(item.get("price_min", 0))),
                        price_max=Decimal(str(item.get("price_max", 0))),
                        currency="CNY",
                        moq=item.get("moq", 1),
                        supplier_name=item.get("supplier_name", ""),
                        supplier_id=item.get("supplier_id", ""),
                        product_url=f"https://detail.1688.com/offer/{item.get('offer_id', '')}.html",
                        category=item.get("category", ""),
                        sales_count=item.get("sales_count", 0),
                        rating=item.get("rating", 0.0),
                    )
                )
            return products

        except Exception as e:
            logger.error("1688 search error: %s", e)
            return []

    async def get_product_detail(self, product_id: str) -> SourceProductDetail:
        """Get detailed product info from 1688."""
        try:
            resp = await self._client.get(
                f"https://api.example.com/1688/product/{product_id}",
                headers={"Authorization": f"Bearer {self._api_key}"},
            )
            resp.raise_for_status()
            item = resp.json()

            return SourceProductDetail(
                source_id=product_id,
                title=item.get("subject", ""),
                title_en=item.get("subject_en", ""),
                description=item.get("description", ""),
                description_html=item.get("description_html", ""),
                images=[img.get("url", "") for img in item.get("images", [])],
                price_min=Decimal(str(item.get("price_min", 0))),
                price_max=Decimal(str(item.get("price_max", 0))),
                currency="CNY",
                moq=item.get("moq", 1),
                supplier_name=item.get("supplier_name", ""),
                supplier_id=item.get("supplier_id", ""),
                product_url=f"https://detail.1688.com/offer/{product_id}.html",
                sku_options=item.get("sku_list", []),
                shipping_templates=item.get("shipping_templates", []),
                supplier_rating=item.get("supplier_rating", 0.0),
                supplier_years=item.get("supplier_years", 0),
                attributes=item.get("attributes", {}),
            )
        except Exception as e:
            logger.error("1688 product detail error: %s", e)
            return SourceProductDetail(source_id=product_id, title="Unknown")

    async def get_shipping_estimate(
        self, product_id: str, destination_country: str, quantity: int
    ) -> Decimal:
        """Estimate shipping cost from China to destination."""
        # Weight-based estimate (rough)
        base_rate_per_kg = {
            "AU": Decimal("8.50"),
            "US": Decimal("7.00"),
            "UK": Decimal("9.00"),
            "GB": Decimal("9.00"),
        }
        rate = base_rate_per_kg.get(destination_country, Decimal("10.00"))
        estimated_weight = Decimal("0.5")  # Assume 500g average
        return (rate * estimated_weight * quantity).quantize(Decimal("0.01"))
