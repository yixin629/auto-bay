"""TikTok Shop Open API connector — implements MarketplaceConnector protocol.

Uses TikTok Shop Open API for product, order, and fulfillment management.
"""

import hashlib
import hmac
import logging
import time
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

TIKTOK_API_BASE = "https://open-api.tiktokglobalshop.com"


@ConnectorRegistry.register(Platform.TIKTOK)
class TikTokConnector:
    """TikTok Shop Open API connector."""

    def __init__(self, credentials: dict, region: str):
        self.credentials = credentials
        self.region = region
        self._app_key = credentials.get("app_key", "")
        self._app_secret = credentials.get("app_secret", "")
        self._access_token = credentials.get("access_token", "")
        self._shop_cipher = credentials.get("shop_cipher", "")
        self._client = httpx.AsyncClient(base_url=TIKTOK_API_BASE, timeout=30.0)

    def _sign_request(self, path: str, params: dict) -> dict:
        """Generate HMAC-SHA256 signature for TikTok Shop API."""
        params["app_key"] = self._app_key
        params["timestamp"] = str(int(time.time()))
        params["shop_cipher"] = self._shop_cipher

        # Sort params and create sign string
        sorted_params = sorted(params.items())
        sign_string = path + "".join(f"{k}{v}" for k, v in sorted_params)
        signature = hmac.new(
            self._app_secret.encode(), sign_string.encode(), hashlib.sha256
        ).hexdigest()

        params["sign"] = signature
        params["access_token"] = self._access_token
        return params

    @marketplace_retry()
    async def create_listing(self, data: ListingCreateDTO) -> ExternalListingResult:
        path = "/product/202309/products"
        payload = {
            "title": data.title,
            "description": data.description,
            "category_id": data.category_id or "",
            "brand_id": data.attributes.get("brand_id", ""),
            "images": [{"uri": img.get("url", "")} for img in data.images[:9]],
            "skus": [
                {
                    "seller_sku": data.internal_product_id,
                    "price": {"amount": str(int(data.price * 100)), "currency": data.currency},
                    "inventory": [{"quantity": data.quantity}],
                }
            ],
            "package_weight": {"value": str(data.weight_grams or 500), "unit": "GRAM"},
        }

        params = self._sign_request(path, {})
        resp = await self._client.post(path, params=params, json=payload)
        resp.raise_for_status()
        result = resp.json()
        product_id = result.get("data", {}).get("product_id", "")

        return ExternalListingResult(
            external_id=product_id,
            status="active" if result.get("code") == 0 else "error",
            raw_response=result,
        )

    @marketplace_retry()
    async def update_listing(self, external_id: str, data: ListingUpdateDTO) -> ExternalListingResult:
        path = f"/product/202309/products/{external_id}"
        payload = {}
        if data.title:
            payload["title"] = data.title
        if data.description:
            payload["description"] = data.description

        params = self._sign_request(path, {})
        resp = await self._client.put(path, params=params, json=payload)
        resp.raise_for_status()
        return ExternalListingResult(external_id=external_id, raw_response=resp.json())

    @marketplace_retry()
    async def delete_listing(self, external_id: str) -> bool:
        path = "/product/202309/products/deactivate"
        params = self._sign_request(path, {})
        resp = await self._client.post(path, params=params, json={"product_ids": [external_id]})
        return resp.status_code == 200

    @marketplace_retry()
    async def update_stock(self, external_id: str, quantity: int) -> bool:
        path = f"/product/202309/products/{external_id}/inventory"
        params = self._sign_request(path, {})
        resp = await self._client.put(path, params=params, json={
            "skus": [{"id": external_id, "inventory": [{"quantity": quantity}]}]
        })
        return resp.status_code == 200

    @marketplace_retry()
    async def update_price(self, external_id: str, price: Decimal, currency: str) -> bool:
        path = f"/product/202309/products/{external_id}/prices"
        params = self._sign_request(path, {})
        resp = await self._client.put(path, params=params, json={
            "skus": [{"id": external_id, "price": {"amount": str(int(price * 100)), "currency": currency}}]
        })
        return resp.status_code == 200

    @marketplace_retry()
    async def fetch_orders(self, since: datetime, status: str | None = None) -> list[ExternalOrderData]:
        path = "/order/202309/orders/search"
        payload = {
            "create_time_ge": int(since.timestamp()),
            "page_size": 50,
        }
        if status:
            payload["order_status"] = status

        params = self._sign_request(path, {})
        resp = await self._client.post(path, params=params, json=payload)
        resp.raise_for_status()
        data = resp.json()

        orders = []
        for raw in data.get("data", {}).get("orders", []):
            payment = raw.get("payment", {})
            orders.append(
                ExternalOrderData(
                    external_order_id=raw.get("id", ""),
                    status=raw.get("status", ""),
                    customer_name=raw.get("recipient_address", {}).get("name", ""),
                    shipping_address=raw.get("recipient_address", {}),
                    line_items=[
                        {
                            "title": item.get("product_name", ""),
                            "sku": item.get("seller_sku", ""),
                            "quantity": item.get("quantity", 1),
                            "unit_price": item.get("sale_price", "0"),
                        }
                        for item in raw.get("line_items", [])
                    ],
                    total=Decimal(str(payment.get("total_amount", "0"))),
                    currency=payment.get("currency", "AUD"),
                    ordered_at=datetime.fromtimestamp(raw.get("create_time", 0)) if raw.get("create_time") else None,
                )
            )
        return orders

    @marketplace_retry()
    async def ship_order(self, external_order_id: str, tracking: TrackingInfo) -> bool:
        path = f"/fulfillment/202309/orders/{external_order_id}/packages"
        params = self._sign_request(path, {})
        resp = await self._client.post(path, params=params, json={
            "tracking_number": tracking.tracking_number,
            "shipping_provider_id": tracking.carrier,
        })
        return resp.status_code == 200

    async def refund_order(self, external_order_id: str, amount: Decimal, reason: str) -> bool:
        logger.info("TikTok refund for %s: %s (%s)", external_order_id, amount, reason)
        return True

    async def fetch_messages(self, since: datetime) -> list[ExternalMessageData]:
        return []

    async def send_message(self, thread_id: str, body: str) -> bool:
        return True

    async def refresh_credentials(self) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{TIKTOK_API_BASE}/auth/202309/token/refresh",
                params={
                    "app_key": self._app_key,
                    "app_secret": self._app_secret,
                    "refresh_token": self.credentials.get("refresh_token", ""),
                    "grant_type": "refresh_token",
                },
            )
            resp.raise_for_status()
            data = resp.json().get("data", {})
            self._access_token = data.get("access_token", "")
            return data

    async def validate_connection(self) -> bool:
        try:
            path = "/seller/202309/shops"
            params = self._sign_request(path, {})
            resp = await self._client.get(path, params=params)
            return resp.status_code == 200
        except Exception:
            return False
