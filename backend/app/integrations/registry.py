"""Connector registry — returns the right connector for a given platform connection."""

from importlib import import_module

from app.integrations.base import MarketplaceConnector
from app.modules.products.models import Platform


class ConnectorRegistry:
    _connectors: dict[Platform, type] = {}
    _platform_modules: dict[Platform, str] = {
        Platform.EBAY: "app.integrations.ebay.client",
        Platform.AMAZON: "app.integrations.amazon.client",
        Platform.SHOPIFY: "app.integrations.shopify.client",
        Platform.TIKTOK: "app.integrations.tiktok.client",
        Platform.DOUYIN: "app.integrations.douyin.client",
        Platform.XIAOHONGSHU: "app.integrations.xiaohongshu.client",
    }

    @classmethod
    def register(cls, platform: Platform):
        def decorator(connector_cls: type):
            cls._connectors[platform] = connector_cls
            return connector_cls
        return decorator

    @classmethod
    def get_connector(cls, platform: Platform, credentials: dict, region: str) -> MarketplaceConnector:
        module_path = cls._platform_modules.get(platform)
        if module_path:
            import_module(module_path)

        connector_cls = cls._connectors.get(platform)
        if not connector_cls:
            raise ValueError(f"No connector registered for platform: {platform}")
        return connector_cls(credentials=credentials, region=region)

    @classmethod
    def available_platforms(cls) -> list[Platform]:
        return list(cls._connectors.keys())
