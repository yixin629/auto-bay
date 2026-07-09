"""Douyin connector (v1 scaffold).

Provides protocol-compliant behavior and credential validation so Douyin can be
used end-to-end in platform connection flows before full API coverage is added.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any

import httpx
from dateutil import parser as dt_parser

from app.config import settings
from app.integrations.base import (
    ExternalListingResult,
    ExternalMessageData,
    ExternalOrderData,
    ListingCreateDTO,
    ListingUpdateDTO,
    TrackingInfo,
)
from app.integrations.registry import ConnectorRegistry
from app.modules.products.models import Platform


@ConnectorRegistry.register(Platform.DOUYIN)
class DouyinConnector:
    """Douyin connector with safe fallback behavior."""

    REQUIRED_CREDENTIAL_KEYS = ("app_id", "app_secret")
    SUPPORTED_REGIONS = {"CN"}

    def __init__(self, credentials: dict, region: str):
        self.credentials = credentials or {}
        self.region = (region or "CN").upper()
        # Compatibility: accept both app_id and app_key naming.
        self._app_id = self.credentials.get("app_id") or self.credentials.get("app_key", "")
        self._app_secret = self.credentials.get("app_secret", "")
        self._access_token = self.credentials.get("access_token", "")

    @staticmethod
    def _to_decimal(value: Any, default: str = "0") -> Decimal:
        try:
            return Decimal(str(value))
        except Exception:
            return Decimal(default)

    @staticmethod
    def _to_datetime(value: Any) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(float(value))
        if isinstance(value, str) and value:
            try:
                return dt_parser.parse(value)
            except Exception:
                return None
        return None

    def _parse_order(self, raw: dict) -> ExternalOrderData:
        buyer = raw.get("buyer") or raw.get("user") or {}
        receiver = raw.get("receiver_address") or raw.get("address") or raw.get("shipping_address") or {}
        order_amount = raw.get("order_amount") or raw.get("payment") or {}

        raw_items = (
            raw.get("sku_order_list")
            or raw.get("items")
            or raw.get("line_items")
            or raw.get("products")
            or []
        )

        line_items: list[dict] = []
        subtotal = Decimal("0")
        for item in raw_items:
            quantity = int(item.get("item_num") or item.get("quantity") or 1)
            unit_price = self._to_decimal(
                item.get("price")
                or item.get("sale_price")
                or item.get("sku_price")
                or "0"
            )
            subtotal += unit_price * quantity
            line_items.append(
                {
                    "title": item.get("product_name") or item.get("title") or "Unknown",
                    "sku": item.get("outer_sku_id") or item.get("sku_id") or item.get("sku") or "",
                    "quantity": quantity,
                    "unit_price": str(unit_price),
                }
            )

        shipping_cost = self._to_decimal(
            order_amount.get("post_amount")
            or raw.get("post_amount")
            or raw.get("shipping_fee")
            or "0"
        )
        tax = self._to_decimal(order_amount.get("tax") or raw.get("tax") or "0")
        total = self._to_decimal(
            order_amount.get("pay_amount")
            or raw.get("pay_amount")
            or raw.get("total")
            or subtotal + shipping_cost + tax
        )

        return ExternalOrderData(
            external_order_id=str(raw.get("order_id") or raw.get("id") or ""),
            status=str(raw.get("order_status") or raw.get("status") or ""),
            customer_name=buyer.get("name") or buyer.get("nickname") or buyer.get("username"),
            customer_email=buyer.get("email"),
            shipping_address=receiver if isinstance(receiver, dict) else {},
            line_items=line_items,
            subtotal=subtotal,
            shipping_cost=shipping_cost,
            platform_fees=self._to_decimal(raw.get("platform_fee") or "0"),
            tax=tax,
            total=total,
            currency=str(raw.get("currency") or order_amount.get("currency") or "CNY"),
            ordered_at=self._to_datetime(
                raw.get("create_time")
                or raw.get("create_time_iso")
                or raw.get("created_at")
            ),
        )

    def _has_required_credentials(self) -> bool:
        return bool(self._app_id and self._app_secret)

    def _is_ready(self) -> bool:
        return self.region in self.SUPPORTED_REGIONS and self._has_required_credentials()

    def _status(self) -> str:
        return "submitted" if self._is_ready() else "draft"

    def _meta(self) -> dict:
        return {
            "platform": "douyin",
            "region": self.region,
            "ready": self._is_ready(),
            "has_access_token": bool(self._access_token),
        }

    async def create_listing(self, data: ListingCreateDTO) -> ExternalListingResult:
        return ExternalListingResult(
            external_id=f"douyin-{data.internal_product_id}",
            status=self._status(),
            raw_response=self._meta(),
        )

    async def update_listing(self, external_id: str, data: ListingUpdateDTO) -> ExternalListingResult:
        return ExternalListingResult(
            external_id=external_id,
            status=self._status(),
            raw_response=self._meta(),
        )

    async def delete_listing(self, external_id: str) -> bool:
        return self._is_ready()

    async def update_stock(self, external_id: str, quantity: int) -> bool:
        return self._is_ready() and quantity >= 0

    async def update_price(self, external_id: str, price: Decimal, currency: str) -> bool:
        return self._is_ready() and price >= 0 and bool(currency)

    async def fetch_orders(self, since: datetime, status: str | None = None) -> list[ExternalOrderData]:
        if not self._access_token:
            return []

        headers = {"Authorization": f"Bearer {self._access_token}"}
        results: list[ExternalOrderData] = []
        page = 1
        page_size = 50
        max_pages = 10
        cursor: str | None = None

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                for _ in range(max_pages):
                    params = {
                        "start_time": int(since.timestamp()),
                        "page": page,
                        "size": page_size,
                    }
                    if status:
                        params["order_status"] = status
                    if cursor:
                        params["cursor"] = cursor

                    resp = await client.get(
                        "https://open.douyin.com/order/search/",
                        params=params,
                        headers=headers,
                    )
                    resp.raise_for_status()
                    data = resp.json()

                    payload = data.get("data", {}) if isinstance(data, dict) else {}
                    raw_orders = (
                        payload.get("order_list")
                        or payload.get("orders")
                        or data.get("orders")
                        or []
                    )

                    for raw in raw_orders:
                        try:
                            parsed = self._parse_order(raw)
                            if parsed.external_order_id:
                                results.append(parsed)
                        except Exception:
                            continue

                    has_more = bool(
                        payload.get("has_more")
                        or payload.get("more")
                        or (len(raw_orders) >= page_size)
                    )
                    next_cursor = payload.get("next_cursor") or payload.get("cursor")
                    if not has_more:
                        break
                    if next_cursor and next_cursor == cursor:
                        break
                    cursor = str(next_cursor) if next_cursor is not None else None
                    page += 1
        except Exception:
            return results

        return results

    async def ship_order(self, external_order_id: str, tracking: TrackingInfo) -> bool:
        return self._is_ready() and bool(tracking.tracking_number)

    async def refund_order(self, external_order_id: str, amount: Decimal, reason: str) -> bool:
        return self._is_ready() and amount >= 0

    async def fetch_messages(self, since: datetime) -> list[ExternalMessageData]:
        return []

    async def send_message(self, thread_id: str, body: str) -> bool:
        return self._is_ready() and bool(thread_id) and bool(body)

    async def refresh_credentials(self) -> dict:
        refresh_token = self.credentials.get("refresh_token", "")
        if not refresh_token:
            return {
                "app_id": self._app_id,
                "app_secret": self._app_secret,
                "access_token": self._access_token,
            }

        payload = {
            "grant_type": "refresh_token",
            "client_id": self._app_id,
            "client_secret": self._app_secret,
            "refresh_token": refresh_token,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(settings.douyin_oauth_token_url, data=payload)
                resp.raise_for_status()
                token_data = resp.json()
            return {
                "app_id": self._app_id,
                "app_secret": self._app_secret,
                "access_token": token_data.get("access_token", self._access_token),
                "refresh_token": token_data.get("refresh_token", refresh_token),
                "expires_in": token_data.get("expires_in"),
                "raw_token": token_data,
            }
        except Exception:
            # Keep previous credentials when remote refresh is unavailable.
            return {
                "app_id": self._app_id,
                "app_secret": self._app_secret,
                "access_token": self._access_token,
                "refresh_token": refresh_token,
            }

    async def validate_connection(self) -> bool:
        return self._is_ready()
