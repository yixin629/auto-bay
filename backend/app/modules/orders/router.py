import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user_id, get_session
from app.modules.orders.schemas import (
    OrderCreate,
    OrderDetailResponse,
    OrderListResponse,
    OrderResponse,
    OrderUpdate,
)
from app.modules.orders.service import create_order, get_order, list_orders, update_order

router = APIRouter()


@router.post("/", response_model=OrderResponse, status_code=201)
async def create(
    data: OrderCreate,
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    return await create_order(session, user_id, data)


@router.get("/", response_model=OrderListResponse)
async def list_all(
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status: str | None = Query(None),
    platform: str | None = Query(None),
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    items, total = await list_orders(session, user_id, offset, limit, status, platform)
    return OrderListResponse(items=items, total=total)


@router.get("/{order_id}", response_model=OrderDetailResponse)
async def get_one(
    order_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    return await get_order(session, user_id, order_id)


@router.patch("/{order_id}", response_model=OrderResponse)
async def update(
    order_id: uuid.UUID,
    data: OrderUpdate,
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    return await update_order(session, user_id, order_id, data)
