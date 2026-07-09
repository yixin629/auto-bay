import pytest

from app.integrations.registry import ConnectorRegistry
from app.integrations.base import ListingCreateDTO
from app.modules.products.models import Platform


@pytest.mark.anyio
async def test_registry_returns_douyin_connector() -> None:
    connector = ConnectorRegistry.get_connector(
        Platform.DOUYIN,
        credentials={"app_key": "k", "app_secret": "s"},
        region="CN",
    )

    assert connector.__class__.__name__ == "DouyinConnector"
    assert await connector.validate_connection() is True


@pytest.mark.anyio
async def test_registry_returns_xiaohongshu_connector() -> None:
    connector = ConnectorRegistry.get_connector(
        Platform.XIAOHONGSHU,
        credentials={"app_id": "id", "app_secret": "secret"},
        region="CN",
    )

    assert connector.__class__.__name__ == "XiaohongshuConnector"
    assert await connector.validate_connection() is True


@pytest.mark.anyio
async def test_cn_connectors_require_supported_region_and_credentials() -> None:
    douyin = ConnectorRegistry.get_connector(
        Platform.DOUYIN,
        credentials={"app_key": "k"},
        region="CN",
    )
    xiaohongshu = ConnectorRegistry.get_connector(
        Platform.XIAOHONGSHU,
        credentials={"app_id": "id", "app_secret": "secret"},
        region="US",
    )

    assert await douyin.validate_connection() is False
    assert await xiaohongshu.validate_connection() is False


@pytest.mark.anyio
async def test_cn_connectors_create_listing_returns_platform_specific_ids() -> None:
    douyin = ConnectorRegistry.get_connector(
        Platform.DOUYIN,
        credentials={"app_id": "id", "app_secret": "secret"},
        region="CN",
    )
    xiaohongshu = ConnectorRegistry.get_connector(
        Platform.XIAOHONGSHU,
        credentials={"client_id": "id", "client_secret": "secret"},
        region="CN",
    )

    payload = ListingCreateDTO(
        internal_product_id="SKU-001",
        title="Test Product",
        description="desc",
        price="19.99",
        currency="CNY",
        quantity=5,
    )

    douyin_result = await douyin.create_listing(payload)
    xhs_result = await xiaohongshu.create_listing(payload)

    assert douyin_result.external_id.startswith("douyin-")
    assert xhs_result.external_id.startswith("xiaohongshu-")
    assert douyin_result.status == "submitted"
    assert xhs_result.status == "submitted"
