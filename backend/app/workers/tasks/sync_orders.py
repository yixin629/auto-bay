"""Periodic task: sync orders from all connected marketplace platforms."""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


async def _sync_orders_async():
    """Async implementation of order sync."""
    from app.db.session import async_session_factory
    from app.integrations.registry import ConnectorRegistry
    from app.modules.orders.models import Order, OrderLineItem, OrderStatus
    from app.modules.products.models import PlatformConnection

    async with async_session_factory() as session:
        # Get all active platform connections
        result = await session.execute(
            select(PlatformConnection).where(PlatformConnection.is_active == True)
        )
        connections = list(result.scalars().all())
        logger.info("Syncing orders for %d platform connections", len(connections))

        for conn in connections:
            try:
                connector = ConnectorRegistry.get_connector(
                    conn.platform, conn.credentials, conn.region
                )

                # Fetch orders since last sync (or last 24h)
                since = conn.last_synced_at or (datetime.now(timezone.utc) - timedelta(hours=24))
                external_orders = await connector.fetch_orders(since)
                logger.info(
                    "[%s/%s] Fetched %d orders",
                    conn.platform.value, conn.region, len(external_orders),
                )

                for ext_order in external_orders:
                    # Check if order already exists
                    existing = await session.execute(
                        select(Order).where(
                            Order.external_order_id == ext_order.external_order_id,
                            Order.platform_connection_id == conn.id,
                        )
                    )
                    if existing.scalar_one_or_none():
                        continue  # Already synced

                    # Create new order
                    order = Order(
                        user_id=conn.user_id,
                        platform_connection_id=conn.id,
                        platform=conn.platform,
                        region=conn.region,
                        external_order_id=ext_order.external_order_id,
                        status=OrderStatus.NEW,
                        customer_name=ext_order.customer_name,
                        customer_email=ext_order.customer_email,
                        shipping_address=ext_order.shipping_address,
                        subtotal=ext_order.subtotal,
                        shipping_cost=ext_order.shipping_cost,
                        platform_fees=ext_order.platform_fees,
                        tax=ext_order.tax,
                        total=ext_order.total,
                        currency=ext_order.currency,
                        ordered_at=ext_order.ordered_at,
                    )
                    session.add(order)
                    await session.flush()

                    # Add line items
                    for li in ext_order.line_items:
                        line_item = OrderLineItem(
                            order_id=order.id,
                            sku=li.get("sku", ""),
                            title=li.get("title", "Unknown"),
                            quantity=li.get("quantity", 1),
                            unit_price=li.get("unit_price", 0),
                            total_price=float(li.get("unit_price", 0)) * li.get("quantity", 1),
                        )
                        session.add(line_item)

                # Update last synced timestamp
                conn.last_synced_at = datetime.now(timezone.utc)
                await session.commit()

            except Exception as e:
                logger.error("[%s/%s] Order sync failed: %s", conn.platform.value, conn.region, e)
                await session.rollback()
                continue


@celery_app.task(name="app.workers.tasks.sync_orders.sync_all_orders", bind=True, max_retries=2)
def sync_all_orders(self):
    """Fetch new orders from all active platform connections and upsert into local DB."""
    logger.info("Starting order sync across all platforms...")
    try:
        asyncio.run(_sync_orders_async())
        logger.info("Order sync completed successfully.")
    except Exception as e:
        logger.error("Order sync failed: %s", e)
        raise self.retry(exc=e, countdown=60)
