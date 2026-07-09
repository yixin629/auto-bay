from datetime import datetime, timedelta, timezone

from app.modules.products.health import compute_platform_connection_health


def test_health_is_critical_when_last_error_exists() -> None:
    result = compute_platform_connection_health(
        last_synced_at=datetime.now(timezone.utc) - timedelta(minutes=10),
        last_sync_error="network timeout",
        stale_threshold_minutes=120,
    )

    assert result.alert_level == "critical"
    assert result.health_score == 20
    assert result.alert_reason == "Last sync failed with error"


def test_health_is_warn_when_never_synced() -> None:
    result = compute_platform_connection_health(
        last_synced_at=None,
        last_sync_error=None,
        stale_threshold_minutes=120,
    )

    assert result.alert_level == "warn"
    assert result.health_score == 55
    assert result.alert_reason == "No successful sync yet"
    assert result.stale_for_seconds is None


def test_health_is_warn_when_sync_is_stale() -> None:
    now = datetime.now(timezone.utc)
    result = compute_platform_connection_health(
        last_synced_at=now - timedelta(hours=3),
        last_sync_error=None,
        stale_threshold_minutes=120,
        now=now,
    )

    assert result.alert_level == "warn"
    assert result.health_score == 55
    assert result.stale_for_seconds == 3 * 3600
    assert result.alert_reason == "No successful sync for 10800s"


def test_health_is_info_when_sync_is_fresh() -> None:
    now = datetime.now(timezone.utc)
    result = compute_platform_connection_health(
        last_synced_at=now - timedelta(minutes=30),
        last_sync_error=None,
        stale_threshold_minutes=120,
        now=now,
    )

    assert result.alert_level == "info"
    assert result.health_score == 100
    assert result.alert_reason == "Connection healthy"
    assert result.stale_for_seconds == 1800
