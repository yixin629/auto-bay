"""Periodic task: sync orders from all connected marketplace platforms."""

import logging

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.workers.tasks.sync_orders.sync_all_orders", bind=True, max_retries=2)
def sync_all_orders(self):
    """Fetch new orders from all active platform connections and upsert into local DB."""
    logger.info("Starting order sync across all platforms...")
    # TODO: Phase 1 implementation
    # 1. Query all active PlatformConnections
    # 2. For each connection, get connector from registry
    # 3. Call connector.fetch_orders(since=last_synced_at)
    # 4. Upsert orders into local orders table
    # 5. Update last_synced_at on platform_connection
    logger.info("Order sync completed.")
