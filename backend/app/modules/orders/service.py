import uuid
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError
from app.modules.orders.models import (
    Order,
    OrderLineItem,
    OrderStatus,
    PaymentStatus,
    Shipment,
)
from app.modules.orders.schemas import OrderCreate, OrderUpdate
from app.modules.products.models import PlatformConnection


async def create_order(
    session: AsyncSession, user_id: uuid.UUID, data: OrderCreate
) -> Order:
    platform = None
    region = None
    if data.platform_connection_id:
        conn = await session.get(PlatformConnection, data.platform_connection_id)
        if conn:
            platform = conn.platform
            region = conn.region

    order = Order(
        user_id=user_id,
        platform_connection_id=data.platform_connection_id,
        platform=platform,
        region=region,
        external_order_id=data.external_order_id,
        customer_name=data.customer_name,
        customer_email=data.customer_email,
        shipping_address=data.shipping_address,
        billing_address=data.billing_address,
        currency=data.currency,
        notes=data.notes,
        ordered_at=data.ordered_at,
    )

    subtotal = Decimal("0")
    for item_data in data.line_items:
        total_price = item_data.unit_price * item_data.quantity
        subtotal += total_price
        line_item = OrderLineItem(
            listing_id=item_data.listing_id,
            product_id=item_data.product_id,
            sku=item_data.sku,
            title=item_data.title,
            quantity=item_data.quantity,
            unit_price=item_data.unit_price,
            total_price=total_price,
        )
        order.line_items.append(line_item)

    order.subtotal = subtotal
    order.total = subtotal

    session.add(order)
    await session.flush()
    return order


async def get_order(session: AsyncSession, user_id: uuid.UUID, order_id: uuid.UUID) -> Order:
    result = await session.execute(
        select(Order)
        .options(selectinload(Order.line_items), selectinload(Order.shipments))
        .where(Order.id == order_id, Order.user_id == user_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise NotFoundError("Order not found")
    return order


async def list_orders(
    session: AsyncSession,
    user_id: uuid.UUID,
    offset: int = 0,
    limit: int = 50,
    status: str | None = None,
    platform: str | None = None,
) -> tuple[list[Order], int]:
    query = select(Order).where(Order.user_id == user_id)
    count_query = select(func.count()).select_from(Order).where(Order.user_id == user_id)

    if status:
        query = query.where(Order.status == OrderStatus(status))
        count_query = count_query.where(Order.status == OrderStatus(status))
    if platform:
        query = query.where(Order.platform == platform)
        count_query = count_query.where(Order.platform == platform)

    query = query.order_by(Order.created_at.desc()).offset(offset).limit(limit)

    result = await session.execute(query)
    total = (await session.execute(count_query)).scalar_one()
    return list(result.scalars().all()), total


async def update_order(
    session: AsyncSession, user_id: uuid.UUID, order_id: uuid.UUID, data: OrderUpdate
) -> Order:
    order = await get_order(session, user_id, order_id)
    update_data = data.model_dump(exclude_unset=True)

    # Handle shipment tracking via a separate shipment record
    tracking_number = update_data.pop("tracking_number", None)
    carrier = update_data.pop("carrier", None)
    if tracking_number:
        shipment = Shipment(
            order_id=order.id,
            carrier=carrier,
            tracking_number=tracking_number,
            shipped_at=update_data.get("shipped_at"),
        )
        session.add(shipment)

    if "status" in update_data and update_data["status"] is not None:
        update_data["status"] = OrderStatus(update_data["status"])
    if "payment_status" in update_data and update_data["payment_status"] is not None:
        update_data["payment_status"] = PaymentStatus(update_data["payment_status"])

    for key, value in update_data.items():
        setattr(order, key, value)

    await session.flush()
    return order
