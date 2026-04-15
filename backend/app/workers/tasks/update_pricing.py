"""Hourly task: recalculate dynamic prices for all non-fixed listings."""

import asyncio
import logging
from decimal import Decimal

from sqlalchemy import select

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


async def _update_pricing_async():
    """Recalculate prices for all dynamic-priced listings."""
    from app.db.session import async_session_factory
    from app.integrations.registry import ConnectorRegistry
    from app.modules.listings.models import Listing, ListingStatus, PricingStrategy
    from app.modules.pricing.service import recalculate_listing_price, record_price_change
    from app.modules.products.models import PlatformConnection, Product

    async with async_session_factory() as session:
        # Get all active listings with non-fixed pricing
        result = await session.execute(
            select(Listing)
            .join(PlatformConnection, Listing.platform_connection_id == PlatformConnection.id)
            .where(
                Listing.status == ListingStatus.ACTIVE,
                Listing.pricing_strategy != PricingStrategy.FIXED,
                PlatformConnection.is_active == True,
            )
        )
        listings = list(result.scalars().all())
        logger.info("Recalculating prices for %d listings", len(listings))

        updated_count = 0
        for listing in listings:
            try:
                product = await session.get(Product, listing.product_id)
                if not product or product.base_cost is None:
                    continue

                new_price = await recalculate_listing_price(
                    session=session,
                    listing_id=listing.id,
                    product_cost=Decimal(str(product.base_cost)),
                    cost_currency=product.base_cost_currency,
                    target_currency=listing.currency,
                    pricing_strategy=listing.pricing_strategy.value,
                    pricing_config=listing.pricing_config,
                    platform=listing.platform.value,
                )

                if new_price is None:
                    continue

                old_price = Decimal(str(listing.price)) if listing.price else Decimal("0")
                if abs(new_price - old_price) < Decimal("0.01"):
                    continue  # No meaningful change

                # Update listing price
                listing.price = new_price

                # Record price change
                await record_price_change(
                    session, listing.id, old_price, new_price,
                    listing.currency, f"auto:{listing.pricing_strategy.value}"
                )

                # Push to platform if listing has external ID
                if listing.external_listing_id:
                    conn = await session.get(PlatformConnection, listing.platform_connection_id)
                    if conn:
                        try:
                            connector = ConnectorRegistry.get_connector(
                                conn.platform, conn.credentials, conn.region
                            )
                            await connector.update_price(
                                listing.external_listing_id, new_price, listing.currency
                            )
                        except Exception as e:
                            logger.warning("Price push failed for %s: %s", listing.id, e)

                updated_count += 1
                logger.debug(
                    "Updated price for listing %s: %s -> %s %s",
                    listing.id, old_price, new_price, listing.currency,
                )

            except Exception as e:
                logger.error("Price recalculation failed for listing %s: %s", listing.id, e)
                continue

        await session.commit()
        logger.info("Updated %d listing prices", updated_count)


@celery_app.task(name="app.workers.tasks.update_pricing.recalculate_all_prices")
def recalculate_all_prices():
    """Recalculate prices for all listings using their pricing strategy."""
    logger.info("Starting price recalculation...")
    try:
        asyncio.run(_update_pricing_async())
        logger.info("Price recalculation completed successfully.")
    except Exception as e:
        logger.error("Price recalculation failed: %s", e)
