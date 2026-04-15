"""Periodic task: push local inventory levels to all platforms."""

import logging

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.workers.tasks.sync_inventory.sync_all_inventory", bind=True, max_retries=2)
def sync_all_inventory(self):
    """Push current stock levels to all active listings across all platforms."""
    logger.info("Starting inventory sync across all platforms...")
    # TODO: Phase 1 implementation
    # 1. Query all active listings with their inventory items
    # 2. For each listing, compute available qty (on_hand - reserved)
    # 3. Call connector.update_stock(external_id, qty)
    # 4. Update last_synced_at
    logger.info("Inventory sync completed.")
