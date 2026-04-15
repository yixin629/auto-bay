"""Periodic task: push local inventory levels to all platform listings."""

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


async def _sync_inventory_async():
    """Async implementation of inventory sync."""
    from app.db.session import async_session_factory
    from app.integrations.registry import ConnectorRegistry
    from app.modules.inventory.models import InventoryItem
    from app.modules.listings.models import Listing, ListingStatus
    from app.modules.products.models import PlatformConnection

    async with async_session_factory() as session:
        # Get all active listings with their platform connections
        result = await session.execute(
            select(Listing)
            .join(PlatformConnection, Listing.platform_connection_id == PlatformConnection.id)
            .where(
                Listing.status == ListingStatus.ACTIVE,
                Listing.external_listing_id.isnot(None),
                PlatformConnection.is_active == True,
            )
        )
        listings = list(result.scalars().all())
        logger.info("Syncing inventory for %d active listings", len(listings))

        for listing in listings:
            try:
                # Get total available stock across all locations
                inv_result = await session.execute(
                    select(InventoryItem).where(
                        InventoryItem.product_id == listing.product_id
                    )
                )
                items = list(inv_result.scalars().all())
                total_available = sum(
                    max(0, item.quantity_on_hand - item.quantity_reserved) for item in items
                )

                # Get the platform connection
                conn = await session.get(PlatformConnection, listing.platform_connection_id)
                if not conn:
                    continue

                connector = ConnectorRegistry.get_connector(
                    conn.platform, conn.credentials, conn.region
                )

                # Push stock level to platform
                success = await connector.update_stock(
                    listing.external_listing_id, total_available
                )
                if success:
                    listing.last_synced_at = datetime.now(timezone.utc)
                    logger.debug(
                        "[%s] Updated stock for %s: %d",
                        listing.platform.value, listing.external_listing_id, total_available,
                    )

            except Exception as e:
                logger.error(
                    "Inventory sync failed for listing %s: %s", listing.id, e
                )
                continue

        await session.commit()


@celery_app.task(name="app.workers.tasks.sync_inventory.sync_all_inventory", bind=True, max_retries=2)
def sync_all_inventory(self):
    """Push current stock levels to all active listings across all platforms."""
    logger.info("Starting inventory sync across all platforms...")
    try:
        asyncio.run(_sync_inventory_async())
        logger.info("Inventory sync completed successfully.")
    except Exception as e:
        logger.error("Inventory sync failed: %s", e)
        raise self.retry(exc=e, countdown=120)
