"""Daily task: fetch latest exchange rates."""

import logging

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.workers.tasks.update_exchange_rates.fetch_rates")
def fetch_rates():
    """Fetch latest exchange rates from API and cache in Redis."""
    logger.info("Fetching exchange rates...")
    # TODO: Call exchangerate.host or Open Exchange Rates API
    # Store CNY->AUD, CNY->USD, CNY->GBP rates in Redis with TTL
    logger.info("Exchange rates updated.")
