import time

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.products.models import PlatformConnection, PlatformSyncEvent


async def record_platform_sync_event(
    session: AsyncSession,
    *,
    connection: PlatformConnection,
    event_type: str,
    status: str,
    message: str | None = None,
    count: int = 0,
    duration_ms: int | None = None,
    details: dict | None = None,
) -> PlatformSyncEvent:
    event = PlatformSyncEvent(
        platform_connection_id=connection.id,
        user_id=connection.user_id,
        platform=connection.platform,
        region=connection.region,
        event_type=event_type,
        status=status,
        message=message,
        count=count,
        duration_ms=duration_ms,
        details=details or {},
    )
    session.add(event)
    await session.flush()
    return event


def now_ms() -> float:
    return time.monotonic() * 1000
