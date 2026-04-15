"""Connector registry — returns the right connector for a given platform connection."""

from app.integrations.base import MarketplaceConnector
from app.modules.products.models import Platform


class ConnectorRegistry:
    _connectors: dict[Platform, type] = {}

    @classmethod
    def register(cls, platform: Platform):
        def decorator(connector_cls: type):
            cls._connectors[platform] = connector_cls
            return connector_cls
        return decorator

    @classmethod
    def get_connector(cls, platform: Platform, credentials: dict, region: str) -> MarketplaceConnector:
        connector_cls = cls._connectors.get(platform)
        if not connector_cls:
            raise ValueError(f"No connector registered for platform: {platform}")
        return connector_cls(credentials=credentials, region=region)

    @classmethod
    def available_platforms(cls) -> list[Platform]:
        return list(cls._connectors.keys())
