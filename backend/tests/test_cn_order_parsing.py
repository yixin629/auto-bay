from datetime import datetime

from app.integrations.douyin.client import DouyinConnector
from app.integrations.xiaohongshu.client import XiaohongshuConnector


def test_douyin_parse_order_maps_core_fields() -> None:
    connector = DouyinConnector(
        credentials={"app_id": "id", "app_secret": "secret", "access_token": "token"},
        region="CN",
    )
    raw = {
        "order_id": "DY-1001",
        "order_status": "PAID",
        "buyer": {"nickname": "alice"},
        "receiver_address": {"city": "Shanghai"},
        "order_amount": {"pay_amount": "88.50", "post_amount": "8.50", "currency": "CNY"},
        "sku_order_list": [
            {"product_name": "Tea Cup", "outer_sku_id": "TC-1", "item_num": 2, "price": "40"}
        ],
        "create_time": datetime(2026, 1, 1, 10, 0, 0).isoformat(),
    }

    parsed = connector._parse_order(raw)

    assert parsed.external_order_id == "DY-1001"
    assert parsed.status == "PAID"
    assert parsed.customer_name == "alice"
    assert parsed.currency == "CNY"
    assert len(parsed.line_items) == 1
    assert parsed.total == 88.50


def test_xiaohongshu_parse_order_maps_core_fields() -> None:
    connector = XiaohongshuConnector(
        credentials={"app_id": "id", "app_secret": "secret", "access_token": "token"},
        region="CN",
    )
    raw = {
        "order_id": "XHS-2001",
        "status": "NEW",
        "buyer": {"name": "bob"},
        "receiver": {"city": "Beijing"},
        "payment": {"total": "120", "shipping_fee": "10", "currency": "CNY"},
        "order_items": [
            {"title": "Bag", "sku": "BG-1", "quantity": 2, "unit_price": "55"}
        ],
        "created_at": datetime(2026, 2, 1, 10, 0, 0).isoformat(),
    }

    parsed = connector._parse_order(raw)

    assert parsed.external_order_id == "XHS-2001"
    assert parsed.status == "NEW"
    assert parsed.customer_name == "bob"
    assert parsed.currency == "CNY"
    assert len(parsed.line_items) == 1
    assert parsed.total == 120
