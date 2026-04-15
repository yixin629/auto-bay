import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user_id, get_session
from app.modules.products.models import ProductStatus
from app.modules.products.schemas import (
    ProductCreate,
    ProductListResponse,
    ProductResponse,
    ProductUpdate,
)
from app.modules.products.service import (
    create_product,
    delete_product,
    get_product,
    list_products,
    update_product,
)

router = APIRouter()


@router.post("/", response_model=ProductResponse, status_code=201)
async def create_product_endpoint(
    data: ProductCreate,
    session: AsyncSession = Depends(get_session),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    product = await create_product(session, user_id, data)
    return product


@router.get("/", response_model=ProductListResponse)
async def list_products_endpoint(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    status: ProductStatus | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    products, total = await list_products(session, user_id, offset, limit, status)
    return ProductListResponse(items=products, total=total)


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product_endpoint(
    product_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    product = await get_product(session, user_id, product_id)
    return product


@router.patch("/{product_id}", response_model=ProductResponse)
async def update_product_endpoint(
    product_id: uuid.UUID,
    data: ProductUpdate,
    session: AsyncSession = Depends(get_session),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    product = await update_product(session, user_id, product_id, data)
    return product


@router.delete("/{product_id}", status_code=204)
async def delete_product_endpoint(
    product_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    await delete_product(session, user_id, product_id)
