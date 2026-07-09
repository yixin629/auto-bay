from datetime import datetime, timezone

from app.modules.products.service import _build_daily_trend_points, _compute_consecutive_error_count


def test_compute_consecutive_error_count_all_error_prefix():
    assert _compute_consecutive_error_count(["error", "error", "success", "error"]) == 2


def test_compute_consecutive_error_count_first_not_error():
    assert _compute_consecutive_error_count(["success", "error", "error"]) == 0


def test_compute_consecutive_error_count_all_error():
    assert _compute_consecutive_error_count(["error", "error", "error"]) == 3


def test_build_daily_trend_points_fills_missing_days():
    now = datetime(2026, 7, 7, 12, 0, tzinfo=timezone.utc)
    rows = [
        {
            "day": datetime(2026, 7, 5, 0, 0, tzinfo=timezone.utc),
            "total_events": 4,
            "success_events": 3,
            "error_events": 1,
            "avg_duration_ms": 1200,
        }
    ]

    points = _build_daily_trend_points(rows, 3, now)

    assert [point["day"] for point in points] == ["2026-07-05", "2026-07-06", "2026-07-07"]
    assert points[0]["success_rate"] == 75.0
    assert points[1]["total_events"] == 0
    assert points[1]["success_rate"] is None
