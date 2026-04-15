"""Daily task: fetch latest exchange rates and cache in DB."""

import asyncio
import logging

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


async def _fetch_rates_async():
    """Fetch and store exchange rates."""
    from app.db.session import async_session_factory
    from app.modules.pricing.models import ExchangeRate
    from app.modules.pricing.service import fetch_exchange_rates_from_api

    rates = await fetch_exchange_rates_from_api()

    async with async_session_factory() as session:
        for base_currency, targets in rates.items():
            for target_currency, rate in targets.items():
                exchange_rate = ExchangeRate(
                    base_currency=base_currency,
                    target_currency=target_currency,
                    rate=rate,
                )
                session.add(exchange_rate)

        await session.commit()
        logger.info("Stored exchange rates: %s", rates)


@celery_app.task(name="app.workers.tasks.update_exchange_rates.fetch_rates")
def fetch_rates():
    """Fetch latest exchange rates from API and store in DB."""
    logger.info("Fetching exchange rates...")
    try:
        asyncio.run(_fetch_rates_async())
        logger.info("Exchange rates updated successfully.")
    except Exception as e:
        logger.error("Exchange rate fetch failed: %s", e)
