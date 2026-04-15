import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user_id, get_session
from app.modules.listings.schemas import (
    ListingCreate,
    ListingListResponse,
    ListingResponse,
    ListingUpdate,
)
from app.modules.listings.service import (
    create_listing,
    delete_listing,
    get_listing,
    list_listings,
    update_listing,
)

router = APIRouter()


@router.post("/", response_model=ListingResponse, status_code=201)
async def create(
    data: ListingCreate,
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    return await create_listing(session, user_id, data)


@router.get("/", response_model=ListingListResponse)
async def list_all(
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    product_id: uuid.UUID | None = Query(None),
    platform: str | None = Query(None),
    status: str | None = Query(None),
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    items, total = await list_listings(session, user_id, offset, limit, product_id, platform, status)
    return ListingListResponse(items=items, total=total)


@router.get("/{listing_id}", response_model=ListingResponse)
async def get_one(
    listing_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    return await get_listing(session, listing_id)


@router.patch("/{listing_id}", response_model=ListingResponse)
async def update(
    listing_id: uuid.UUID,
    data: ListingUpdate,
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    return await update_listing(session, listing_id, data)


@router.delete("/{listing_id}", status_code=204)
async def delete(
    listing_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    await delete_listing(session, listing_id)
