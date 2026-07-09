from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(slots=True)
class PlatformConnectionHealth:
    alert_level: str
    alert_reason: str
    health_score: int
    stale_for_seconds: int | None


def compute_platform_connection_health(
    *,
    last_synced_at: datetime | None,
    last_sync_error: str | None,
    stale_threshold_minutes: int,
    now: datetime | None = None,
) -> PlatformConnectionHealth:
    current = now or datetime.now(timezone.utc)

    stale_for_seconds: int | None = None
    if last_synced_at is not None:
        delta = current - last_synced_at
        stale_for_seconds = max(0, int(delta.total_seconds()))

    stale_threshold_seconds = stale_threshold_minutes * 60
    is_stale = stale_for_seconds is None or stale_for_seconds > stale_threshold_seconds

    if last_sync_error:
        return PlatformConnectionHealth(
            alert_level="critical",
            alert_reason="Last sync failed with error",
            health_score=20,
            stale_for_seconds=stale_for_seconds,
        )

    if is_stale:
        if stale_for_seconds is None:
            reason = "No successful sync yet"
        else:
            reason = f"No successful sync for {stale_for_seconds}s"
        return PlatformConnectionHealth(
            alert_level="warn",
            alert_reason=reason,
            health_score=55,
            stale_for_seconds=stale_for_seconds,
        )

    return PlatformConnectionHealth(
        alert_level="info",
        alert_reason="Connection healthy",
        health_score=100,
        stale_for_seconds=stale_for_seconds,
    )
