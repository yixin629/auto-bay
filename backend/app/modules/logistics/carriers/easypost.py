"""EasyPost/ShipStation integration for multi-carrier shipping.

EasyPost provides a unified API for USPS, UPS, FedEx, Australia Post,
Royal Mail, DHL, and many more carriers.
"""

import logging
from decimal import Decimal

import httpx

from app.modules.logistics.carriers.base import (
    ShipmentLabel,
    ShipmentRequest,
    ShippingRate,
    TrackingEvent,
    TrackingStatus,
)

logger = logging.getLogger(__name__)

EASYPOST_API = "https://api.easypost.com/v2"


class EasyPostAdapter:
    """EasyPost multi-carrier shipping integration."""

    def __init__(self, api_key: str):
        self._api_key = api_key
        self._client = httpx.AsyncClient(
            base_url=EASYPOST_API,
            timeout=30.0,
            auth=(api_key, ""),
        )

    async def get_rates(self, request: ShipmentRequest) -> list[ShippingRate]:
        payload = {
            "shipment": {
                "from_address": self._format_address(request.from_address),
                "to_address": self._format_address(request.to_address),
                "parcel": {
                    "weight": request.weight_grams / 28.35,  # Convert to oz
                },
                "customs_info": {
                    "customs_items": [
                        {
                            "description": "Merchandise",
                            "quantity": 1,
                            "weight": request.weight_grams / 28.35,
                            "value": float(request.declared_value),
                            "origin_country": request.from_address.get("country", "CN"),
                        }
                    ],
                } if request.from_address.get("country") != request.to_address.get("country") else None,
            }
        }

        resp = await self._client.post("/shipments", json=payload)
        resp.raise_for_status()
        data = resp.json()

        rates = []
        for rate in data.get("rates", []):
            rates.append(
                ShippingRate(
                    carrier=rate.get("carrier", ""),
                    service=rate.get("service", ""),
                    rate=Decimal(rate.get("rate", "0")),
                    currency=rate.get("currency", "USD"),
                    estimated_days=rate.get("est_delivery_days", 7),
                )
            )
        return sorted(rates, key=lambda r: r.rate)

    async def create_shipment(self, request: ShipmentRequest) -> ShipmentLabel:
        # First get rates
        rates = await self.get_rates(request)
        if not rates:
            raise ValueError("No shipping rates available")

        # Buy the cheapest rate that matches service type
        preferred = [r for r in rates if request.service_type in r.service.lower()]
        chosen_rate = preferred[0] if preferred else rates[0]

        # In a real implementation, we'd call the buy endpoint
        # For now, return a placeholder
        return ShipmentLabel(
            shipment_id="shp_placeholder",
            tracking_number="TRACK_PLACEHOLDER",
            carrier=chosen_rate.carrier,
            label_url="https://easypost.com/label/placeholder.pdf",
        )

    async def track_shipment(self, tracking_number: str) -> TrackingStatus:
        resp = await self._client.get(
            f"/trackers",
            params={"tracking_code": tracking_number},
        )
        resp.raise_for_status()
        data = resp.json()

        tracker = data.get("trackers", [{}])[0] if data.get("trackers") else {}
        events = [
            TrackingEvent(
                timestamp=e.get("datetime", ""),
                status=e.get("status", ""),
                location=f"{e.get('tracking_location', {}).get('city', '')}, {e.get('tracking_location', {}).get('country', '')}",
                description=e.get("message", ""),
            )
            for e in tracker.get("tracking_details", [])
        ]

        return TrackingStatus(
            tracking_number=tracking_number,
            carrier=tracker.get("carrier", ""),
            status=tracker.get("status", "unknown"),
            estimated_delivery=tracker.get("est_delivery_date"),
            events=events,
        )

    async def cancel_shipment(self, shipment_id: str) -> bool:
        resp = await self._client.post(f"/shipments/{shipment_id}/refund")
        return resp.status_code == 200

    @staticmethod
    def _format_address(address: dict) -> dict:
        return {
            "name": address.get("name", ""),
            "street1": address.get("street1", address.get("address1", "")),
            "street2": address.get("street2", address.get("address2", "")),
            "city": address.get("city", ""),
            "state": address.get("state", address.get("province", "")),
            "zip": address.get("zip", address.get("postal_code", "")),
            "country": address.get("country", ""),
            "phone": address.get("phone", ""),
        }
