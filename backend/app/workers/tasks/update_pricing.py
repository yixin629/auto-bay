"""Hourly task: recalculate dynamic prices for all listings."""

import logging

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.workers.tasks.update_pricing.recalculate_all_prices")
def recalculate_all_prices():
    """Recalculate prices for all listings using their pricing strategy."""
    logger.info("Starting price recalculation...")
    # TODO: Phase 3 implementation
    # 1. Query all active listings with pricing_strategy != 'fixed'
    # 2. For each listing, compute new price based on strategy
    # 3. If price changed, call connector.update_price()
    logger.info("Price recalculation completed.")
