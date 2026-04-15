import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user_id, get_session
from app.modules.inventory.schemas import (
    InventoryItemResponse,
    LocationCreate,
    LocationResponse,
    StockAdjustment,
)
from app.modules.inventory.service import (
    adjust_stock,
    create_location,
    get_product_stock,
    list_locations,
)

router = APIRouter()


@router.post("/locations", response_model=LocationResponse, status_code=201)
async def create_loc(
    data: LocationCreate,
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    return await create_location(session, user_id, data)


@router.get("/locations", response_model=list[LocationResponse])
async def list_locs(
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    return await list_locations(session, user_id)


@router.get("/products/{product_id}", response_model=list[InventoryItemResponse])
async def get_stock(
    product_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    items = await get_product_stock(session, product_id)
    return [
        InventoryItemResponse(
            id=item.id,
            product_id=item.product_id,
            location_id=item.location_id,
            quantity_on_hand=item.quantity_on_hand,
            quantity_reserved=item.quantity_reserved,
            quantity_available=item.quantity_on_hand - item.quantity_reserved,
            reorder_point=item.reorder_point,
            reorder_quantity=item.reorder_quantity,
            updated_at=item.updated_at,
        )
        for item in items
    ]


@router.post("/adjust", response_model=InventoryItemResponse)
async def adjust(
    data: StockAdjustment,
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    item = await adjust_stock(session, data)
    return InventoryItemResponse(
        id=item.id,
        product_id=item.product_id,
        location_id=item.location_id,
        quantity_on_hand=item.quantity_on_hand,
        quantity_reserved=item.quantity_reserved,
        quantity_available=item.quantity_on_hand - item.quantity_reserved,
        reorder_point=item.reorder_point,
        reorder_quantity=item.reorder_quantity,
        updated_at=item.updated_at,
    )
