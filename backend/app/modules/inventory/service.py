import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError, NotFoundError
from app.modules.inventory.models import (
    InventoryItem,
    InventoryLocation,
    InventoryMovement,
    LocationType,
    MovementType,
)
from app.modules.inventory.schemas import LocationCreate, StockAdjustment


async def create_location(
    session: AsyncSession, user_id: uuid.UUID, data: LocationCreate
) -> InventoryLocation:
    location = InventoryLocation(
        user_id=user_id,
        name=data.name,
        country=data.country,
        address=data.address,
        location_type=LocationType(data.location_type),
    )
    session.add(location)
    await session.flush()
    return location


async def list_locations(
    session: AsyncSession, user_id: uuid.UUID
) -> list[InventoryLocation]:
    result = await session.execute(
        select(InventoryLocation)
        .where(InventoryLocation.user_id == user_id)
        .order_by(InventoryLocation.name)
    )
    return list(result.scalars().all())


async def get_product_stock(
    session: AsyncSession, product_id: uuid.UUID
) -> list[InventoryItem]:
    result = await session.execute(
        select(InventoryItem).where(InventoryItem.product_id == product_id)
    )
    return list(result.scalars().all())


async def _get_or_create_inventory_item(
    session: AsyncSession, product_id: uuid.UUID, location_id: uuid.UUID
) -> InventoryItem:
    result = await session.execute(
        select(InventoryItem).where(
            InventoryItem.product_id == product_id,
            InventoryItem.location_id == location_id,
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        item = InventoryItem(product_id=product_id, location_id=location_id)
        session.add(item)
        await session.flush()
    return item


async def adjust_stock(session: AsyncSession, data: StockAdjustment) -> InventoryItem:
    item = await _get_or_create_inventory_item(session, data.product_id, data.location_id)

    new_quantity = item.quantity_on_hand + data.quantity_change
    if new_quantity < 0:
        raise BadRequestError(
            f"Insufficient stock. Current: {item.quantity_on_hand}, change: {data.quantity_change}"
        )

    item.quantity_on_hand = new_quantity

    movement = InventoryMovement(
        inventory_item_id=item.id,
        movement_type=MovementType(data.movement_type),
        quantity_change=data.quantity_change,
        reference_type=data.reference_type,
        reference_id=data.reference_id,
        notes=data.notes,
    )
    session.add(movement)
    await session.flush()
    return item


async def reserve_stock(
    session: AsyncSession, product_id: uuid.UUID, location_id: uuid.UUID, quantity: int
) -> InventoryItem:
    item = await _get_or_create_inventory_item(session, product_id, location_id)
    available = item.quantity_on_hand - item.quantity_reserved
    if quantity > available:
        raise BadRequestError(
            f"Insufficient available stock. Available: {available}, requested: {quantity}"
        )
    item.quantity_reserved += quantity
    await session.flush()
    return item


async def release_stock(
    session: AsyncSession, product_id: uuid.UUID, location_id: uuid.UUID, quantity: int
) -> InventoryItem:
    item = await _get_or_create_inventory_item(session, product_id, location_id)
    item.quantity_reserved = max(0, item.quantity_reserved - quantity)
    await session.flush()
    return item
