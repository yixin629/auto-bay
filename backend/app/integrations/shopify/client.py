"""Shopify GraphQL Admin API connector — implements MarketplaceConnector protocol.

Uses GraphQL Admin API (REST is deprecated for new apps since April 2025).
API version: 2025-04.
"""

import logging
from datetime import datetime
from decimal import Decimal

import httpx

from app.integrations.base import (
    ExternalListingResult,
    ExternalMessageData,
    ExternalOrderData,
    ListingCreateDTO,
    ListingUpdateDTO,
    TrackingInfo,
)
from app.integrations.registry import ConnectorRegistry
from app.integrations.retry import marketplace_retry
from app.modules.products.models import Platform

logger = logging.getLogger(__name__)


@ConnectorRegistry.register(Platform.SHOPIFY)
class ShopifyConnector:
    """Shopify GraphQL Admin API connector."""

    def __init__(self, credentials: dict, region: str):
        self.credentials = credentials
        self.region = region
        self._store_url = credentials.get("store_url", "")
        self._access_token = credentials.get("access_token", "")
        self._api_version = "2025-04"
        self._graphql_url = f"https://{self._store_url}/admin/api/{self._api_version}/graphql.json"
        self._client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "X-Shopify-Access-Token": self._access_token,
                "Content-Type": "application/json",
            },
        )

    async def _graphql(self, query: str, variables: dict | None = None) -> dict:
        payload = {"query": query}
        if variables:
            payload["variables"] = variables
        resp = await self._client.post(self._graphql_url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        if "errors" in data:
            logger.error("Shopify GraphQL errors: %s", data["errors"])
        return data.get("data", {})

    @marketplace_retry()
    async def create_listing(self, data: ListingCreateDTO) -> ExternalListingResult:
        mutation = """
        mutation productCreate($input: ProductInput!) {
          productCreate(input: $input) {
            product {
              id
              handle
              onlineStoreUrl
            }
            userErrors { field message }
          }
        }
        """
        images = [{"src": img.get("url", ""), "altText": img.get("alt_text", "")} for img in data.images[:20]]

        variables = {
            "input": {
                "title": data.title,
                "descriptionHtml": data.description_html or data.description,
                "productType": data.attributes.get("product_type", ""),
                "vendor": data.attributes.get("brand", ""),
                "tags": data.attributes.get("tags", []),
                "images": images,
                "variants": [
                    {
                        "price": str(data.price),
                        "sku": data.internal_product_id,
                        "inventoryQuantities": [
                            {
                                "availableQuantity": data.quantity,
                                "locationId": self.credentials.get("location_id", ""),
                            }
                        ],
                    }
                ],
            }
        }

        result = await self._graphql(mutation, variables)
        product_data = result.get("productCreate", {}).get("product", {})
        product_id = product_data.get("id", "")

        return ExternalListingResult(
            external_id=product_id,
            external_url=product_data.get("onlineStoreUrl", f"https://{self._store_url}/products/{product_data.get('handle', '')}"),
            status="active",
            raw_response=result,
        )

    @marketplace_retry()
    async def update_listing(self, external_id: str, data: ListingUpdateDTO) -> ExternalListingResult:
        mutation = """
        mutation productUpdate($input: ProductInput!) {
          productUpdate(input: $input) {
            product { id handle }
            userErrors { field message }
          }
        }
        """
        input_data: dict = {"id": external_id}
        if data.title:
            input_data["title"] = data.title
        if data.description:
            input_data["descriptionHtml"] = data.description

        result = await self._graphql(mutation, {"input": input_data})
        return ExternalListingResult(external_id=external_id, raw_response=result)

    @marketplace_retry()
    async def delete_listing(self, external_id: str) -> bool:
        mutation = """
        mutation productDelete($input: ProductDeleteInput!) {
          productDelete(input: $input) {
            deletedProductId
            userErrors { field message }
          }
        }
        """
        result = await self._graphql(mutation, {"input": {"id": external_id}})
        return bool(result.get("productDelete", {}).get("deletedProductId"))

    @marketplace_retry()
    async def update_stock(self, external_id: str, quantity: int) -> bool:
        # First get the inventory item ID
        query = """
        query getProduct($id: ID!) {
          product(id: $id) {
            variants(first: 1) {
              edges {
                node {
                  inventoryItem { id }
                }
              }
            }
          }
        }
        """
        result = await self._graphql(query, {"id": external_id})
        edges = result.get("product", {}).get("variants", {}).get("edges", [])
        if not edges:
            return False

        inventory_item_id = edges[0]["node"]["inventoryItem"]["id"]
        location_id = self.credentials.get("location_id", "")

        mutation = """
        mutation inventoryAdjustQuantities($input: InventoryAdjustQuantitiesInput!) {
          inventoryAdjustQuantities(input: $input) {
            userErrors { field message }
          }
        }
        """
        result = await self._graphql(mutation, {
            "input": {
                "reason": "correction",
                "name": "available",
                "changes": [
                    {
                        "delta": quantity,
                        "inventoryItemId": inventory_item_id,
                        "locationId": location_id,
                    }
                ],
            }
        })
        return not result.get("inventoryAdjustQuantities", {}).get("userErrors")

    @marketplace_retry()
    async def update_price(self, external_id: str, price: Decimal, currency: str) -> bool:
        # Get first variant ID, then update price
        query = """
        query getProduct($id: ID!) {
          product(id: $id) {
            variants(first: 1) { edges { node { id } } }
          }
        }
        """
        result = await self._graphql(query, {"id": external_id})
        edges = result.get("product", {}).get("variants", {}).get("edges", [])
        if not edges:
            return False

        variant_id = edges[0]["node"]["id"]
        mutation = """
        mutation productVariantUpdate($input: ProductVariantInput!) {
          productVariantUpdate(input: $input) {
            productVariant { id price }
            userErrors { field message }
          }
        }
        """
        result = await self._graphql(mutation, {"input": {"id": variant_id, "price": str(price)}})
        return not result.get("productVariantUpdate", {}).get("userErrors")

    @marketplace_retry()
    async def fetch_orders(self, since: datetime, status: str | None = None) -> list[ExternalOrderData]:
        query = """
        query getOrders($query: String!) {
          orders(first: 50, query: $query) {
            edges {
              node {
                id name
                displayFinancialStatus displayFulfillmentStatus
                createdAt
                totalPriceSet { shopMoney { amount currencyCode } }
                customer { displayName email }
                shippingAddress { address1 address2 city province zip country }
                lineItems(first: 50) {
                  edges {
                    node { title sku quantity
                      originalUnitPriceSet { shopMoney { amount } }
                    }
                  }
                }
              }
            }
          }
        }
        """
        filter_query = f"created_at:>'{since.strftime('%Y-%m-%dT%H:%M:%S')}'"
        if status:
            filter_query += f" fulfillment_status:{status}"

        result = await self._graphql(query, {"query": filter_query})
        orders = []
        for edge in result.get("orders", {}).get("edges", []):
            node = edge["node"]
            total = node.get("totalPriceSet", {}).get("shopMoney", {})
            customer = node.get("customer", {}) or {}
            line_items = [
                {
                    "title": li["node"]["title"],
                    "sku": li["node"].get("sku", ""),
                    "quantity": li["node"]["quantity"],
                    "unit_price": li["node"].get("originalUnitPriceSet", {}).get("shopMoney", {}).get("amount", "0"),
                }
                for li in node.get("lineItems", {}).get("edges", [])
            ]
            orders.append(
                ExternalOrderData(
                    external_order_id=node.get("name", node["id"]),
                    status=node.get("displayFulfillmentStatus", "UNFULFILLED"),
                    customer_name=customer.get("displayName", ""),
                    customer_email=customer.get("email", ""),
                    shipping_address=node.get("shippingAddress", {}),
                    line_items=line_items,
                    total=Decimal(total.get("amount", "0")),
                    currency=total.get("currencyCode", "AUD"),
                    ordered_at=node.get("createdAt"),
                )
            )
        return orders

    @marketplace_retry()
    async def ship_order(self, external_order_id: str, tracking: TrackingInfo) -> bool:
        mutation = """
        mutation fulfillmentCreateV2($fulfillment: FulfillmentV2Input!) {
          fulfillmentCreateV2(fulfillment: $fulfillment) {
            fulfillment { id status }
            userErrors { field message }
          }
        }
        """
        result = await self._graphql(mutation, {
            "fulfillment": {
                "lineItemsByFulfillmentOrder": [
                    {"fulfillmentOrderId": external_order_id}
                ],
                "trackingInfo": {
                    "company": tracking.carrier,
                    "number": tracking.tracking_number,
                },
            }
        })
        return not result.get("fulfillmentCreateV2", {}).get("userErrors")

    async def refund_order(self, external_order_id: str, amount: Decimal, reason: str) -> bool:
        logger.info("Shopify refund for order %s: %s (%s)", external_order_id, amount, reason)
        return True

    async def fetch_messages(self, since: datetime) -> list[ExternalMessageData]:
        return []

    async def send_message(self, thread_id: str, body: str) -> bool:
        return True

    async def refresh_credentials(self) -> dict:
        return self.credentials

    async def validate_connection(self) -> bool:
        try:
            result = await self._graphql("{ shop { name } }")
            return bool(result.get("shop", {}).get("name"))
        except Exception:
            return False
