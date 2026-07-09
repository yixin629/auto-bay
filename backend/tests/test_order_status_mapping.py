from app.modules.orders.models import OrderStatus
from app.workers.tasks.sync_orders import _map_external_status


def test_map_external_status_known_values() -> None:
    assert _map_external_status("paid") == OrderStatus.AWAITING_SHIPMENT
    assert _map_external_status("shipped") == OrderStatus.SHIPPED
    assert _map_external_status("completed") == OrderStatus.COMPLETED
    assert _map_external_status("refunded") == OrderStatus.REFUNDED


def test_map_external_status_unknown_defaults_to_new() -> None:
    assert _map_external_status("unknown_status") == OrderStatus.NEW
    assert _map_external_status(None) == OrderStatus.NEW
