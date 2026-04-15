import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.config import settings
from app.db.base import Base

# Import all models so Alembic can detect them
from app.modules.auth.models import User  # noqa: F401
from app.modules.products.models import PlatformConnection, Product, ProductTranslation  # noqa: F401
from app.modules.listings.models import Listing  # noqa: F401
from app.modules.orders.models import Order, OrderLineItem, Shipment  # noqa: F401
from app.modules.inventory.models import InventoryItem, InventoryLocation, InventoryMovement  # noqa: F401
from app.modules.pricing.models import ExchangeRate, PriceHistory  # noqa: F401
from app.modules.customer_service.models import CustomerMessage  # noqa: F401
from app.modules.marketing.models import AITask, MarketingCampaign  # noqa: F401

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
