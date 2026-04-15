import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.modules.listings.models import Listing, ListingStatus, PricingStrategy
from app.modules.listings.schemas import ListingCreate, ListingUpdate
from app.modules.products.models import PlatformConnection


async def create_listing(
    session: AsyncSession, user_id: uuid.UUID, data: ListingCreate
) -> Listing:
    conn = await session.get(PlatformConnection, data.platform_connection_id)
    if not conn or conn.user_id != user_id:
        raise NotFoundError("Platform connection not found")

    listing = Listing(
        product_id=data.product_id,
        platform_connection_id=data.platform_connection_id,
        platform=conn.platform,
        region=conn.region,
        title=data.title,
        price=data.price,
        currency=data.currency,
        pricing_strategy=PricingStrategy(data.pricing_strategy),
        pricing_config=data.pricing_config,
    )
    session.add(listing)
    await session.flush()
    return listing


async def get_listing(session: AsyncSession, listing_id: uuid.UUID) -> Listing:
    listing = await session.get(Listing, listing_id)
    if not listing:
        raise NotFoundError("Listing not found")
    return listing


async def list_listings(
    session: AsyncSession,
    user_id: uuid.UUID,
    offset: int = 0,
    limit: int = 50,
    product_id: uuid.UUID | None = None,
    platform: str | None = None,
    status: str | None = None,
) -> tuple[list[Listing], int]:
    # Join with platform_connections to filter by user
    query = (
        select(Listing)
        .join(PlatformConnection, Listing.platform_connection_id == PlatformConnection.id)
        .where(PlatformConnection.user_id == user_id)
    )
    count_query = (
        select(func.count())
        .select_from(Listing)
        .join(PlatformConnection, Listing.platform_connection_id == PlatformConnection.id)
        .where(PlatformConnection.user_id == user_id)
    )

    if product_id:
        query = query.where(Listing.product_id == product_id)
        count_query = count_query.where(Listing.product_id == product_id)
    if platform:
        query = query.where(Listing.platform == platform)
        count_query = count_query.where(Listing.platform == platform)
    if status:
        query = query.where(Listing.status == ListingStatus(status))
        count_query = count_query.where(Listing.status == ListingStatus(status))

    query = query.order_by(Listing.created_at.desc()).offset(offset).limit(limit)

    result = await session.execute(query)
    total = (await session.execute(count_query)).scalar_one()
    return list(result.scalars().all()), total


async def update_listing(
    session: AsyncSession, listing_id: uuid.UUID, data: ListingUpdate
) -> Listing:
    listing = await get_listing(session, listing_id)
    update_data = data.model_dump(exclude_unset=True)

    if "status" in update_data and update_data["status"] is not None:
        update_data["status"] = ListingStatus(update_data["status"])
    if "pricing_strategy" in update_data and update_data["pricing_strategy"] is not None:
        update_data["pricing_strategy"] = PricingStrategy(update_data["pricing_strategy"])

    for key, value in update_data.items():
        setattr(listing, key, value)

    await session.flush()
    return listing


async def delete_listing(session: AsyncSession, listing_id: uuid.UUID) -> None:
    listing = await get_listing(session, listing_id)
    await session.delete(listing)
    await session.flush()
