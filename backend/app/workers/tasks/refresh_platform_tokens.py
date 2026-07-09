"""Periodic task: refresh marketplace OAuth tokens for active platform connections."""

import asyncio
import logging
import time
from datetime import datetime, timezone

from sqlalchemy import select

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


async def _refresh_tokens_async() -> None:
    from app.core.security import decrypt_credentials, encrypt_credentials
    from app.db.session import async_session_factory
    from app.integrations.registry import ConnectorRegistry
    from app.modules.products.audit import record_platform_sync_event
    from app.modules.products.models import Platform, PlatformConnection

    oauth_platforms = [Platform.DOUYIN, Platform.XIAOHONGSHU]

    async with async_session_factory() as session:
        result = await session.execute(
            select(PlatformConnection).where(
                PlatformConnection.is_active == True,
                PlatformConnection.platform.in_(oauth_platforms),
            )
        )
        connections = list(result.scalars().all())
        logger.info("Refreshing OAuth tokens for %d platform connections", len(connections))

        for conn in connections:
            started_ms = time.monotonic() * 1000
            try:
                credentials = decrypt_credentials(conn.credentials)
                connector = ConnectorRegistry.get_connector(
                    conn.platform,
                    credentials,
                    conn.region,
                )
                refreshed = await connector.refresh_credentials()
                refreshed_count = 0
                if refreshed:
                    conn.credentials = encrypt_credentials(refreshed)
                    conn.updated_at = datetime.now(timezone.utc)
                    refreshed_count = 1

                await record_platform_sync_event(
                    session,
                    connection=conn,
                    event_type="token_refresh",
                    status="success",
                    message="Token refresh completed",
                    count=refreshed_count,
                    duration_ms=int(time.monotonic() * 1000 - started_ms),
                )
            except Exception as exc:
                logger.warning(
                    "[%s/%s] token refresh failed: %s",
                    conn.platform.value,
                    conn.region,
                    exc,
                )
                await record_platform_sync_event(
                    session,
                    connection=conn,
                    event_type="token_refresh",
                    status="error",
                    message=str(exc)[:1000],
                    count=0,
                    duration_ms=int(time.monotonic() * 1000 - started_ms),
                )
                continue

        await session.commit()


@celery_app.task(
    name="app.workers.tasks.refresh_platform_tokens.refresh_oauth_tokens",
    bind=True,
    max_retries=2,
)
def refresh_oauth_tokens(self):
    """Refresh OAuth access tokens for supported connected marketplaces."""
    logger.info("Starting OAuth token refresh task...")
    try:
        asyncio.run(_refresh_tokens_async())
        logger.info("OAuth token refresh completed successfully.")
    except Exception as exc:
        logger.error("OAuth token refresh failed: %s", exc)
        raise self.retry(exc=exc, countdown=300)
