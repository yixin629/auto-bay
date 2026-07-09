import uuid
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import decrypt_credentials
from app.dependencies import get_current_user_id, get_session
from app.modules.products.health import compute_platform_connection_health
from app.modules.products.models import Platform, PlatformConnection, ProductStatus
from app.modules.products.schemas import (
    PlatformConnectionCreate,
    PlatformConnectionListResponse,
    PlatformConnectionResponse,
    PlatformConnectionTestResult,
    PlatformConnectionUpdate,
    PlatformSyncEventListResponse,
    PlatformSyncMetricsResponse,
    PlatformOAuthCallbackResponse,
    PlatformOAuthStartRequest,
    PlatformOAuthStartResponse,
    ProductCreate,
    ProductListResponse,
    ProductResponse,
    ProductUpdate,
)
from app.modules.products.service import (
    build_platform_oauth_start,
    create_platform_connection,
    create_product,
    delete_platform_connection,
    delete_product,
    exchange_platform_oauth_callback,
    get_platform_connection,
    get_platform_sync_metrics,
    get_product,
    list_platform_connections,
    list_platform_sync_events,
    list_products,
    test_platform_connection,
    update_platform_connection,
    update_product,
)

router = APIRouter()


def _oauth_redirect_url(status: str, platform: str, region: str, message: str) -> str:
    params = urlencode(
        {
            "oauth_status": status,
            "oauth_platform": platform,
            "oauth_region": region,
            "oauth_message": message,
        }
    )
    return f"{settings.frontend_url}/dashboard/settings?{params}"


def _to_platform_connection_response(conn: PlatformConnection) -> PlatformConnectionResponse:
    credentials = decrypt_credentials(conn.credentials)
    health = compute_platform_connection_health(
        last_synced_at=conn.last_synced_at,
        last_sync_error=conn.last_sync_error,
        stale_threshold_minutes=settings.sync_stale_threshold_minutes,
    )

    return PlatformConnectionResponse(
        id=conn.id,
        user_id=conn.user_id,
        platform=conn.platform,
        region=conn.region,
        account_name=conn.account_name,
        has_credentials=bool(credentials),
        credential_keys=sorted(list(credentials.keys())),
        is_active=conn.is_active,
        last_synced_at=conn.last_synced_at,
        last_sync_count=conn.last_sync_count,
        last_sync_error=conn.last_sync_error,
        alert_level=health.alert_level,
        alert_reason=health.alert_reason,
        health_score=health.health_score,
        stale_for_seconds=health.stale_for_seconds,
        created_at=conn.created_at,
        updated_at=conn.updated_at,
    )


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


@router.post("/platform-connections", response_model=PlatformConnectionResponse, status_code=201)
async def create_platform_connection_endpoint(
    data: PlatformConnectionCreate,
    session: AsyncSession = Depends(get_session),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    conn = await create_platform_connection(session, user_id, data)
    return _to_platform_connection_response(conn)


@router.get("/platform-connections", response_model=PlatformConnectionListResponse)
async def list_platform_connections_endpoint(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    platform: Platform | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    items, total = await list_platform_connections(
        session=session,
        user_id=user_id,
        offset=offset,
        limit=limit,
        platform=platform,
    )
    return PlatformConnectionListResponse(
        items=[_to_platform_connection_response(item) for item in items],
        total=total,
    )


@router.get("/platform-connections/{connection_id}", response_model=PlatformConnectionResponse)
async def get_platform_connection_endpoint(
    connection_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    conn = await get_platform_connection(session, user_id, connection_id)
    return _to_platform_connection_response(conn)


@router.patch("/platform-connections/{connection_id}", response_model=PlatformConnectionResponse)
async def update_platform_connection_endpoint(
    connection_id: uuid.UUID,
    data: PlatformConnectionUpdate,
    session: AsyncSession = Depends(get_session),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    conn = await update_platform_connection(session, user_id, connection_id, data)
    return _to_platform_connection_response(conn)


@router.post("/platform-connections/{connection_id}/test", response_model=PlatformConnectionTestResult)
async def test_platform_connection_endpoint(
    connection_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    platform, region, ok = await test_platform_connection(session, user_id, connection_id)
    return PlatformConnectionTestResult(
        ok=ok,
        platform=platform,
        region=region,
        message="Connection validated" if ok else "Connection validation failed",
    )


@router.delete("/platform-connections/{connection_id}", status_code=204)
async def delete_platform_connection_endpoint(
    connection_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    await delete_platform_connection(session, user_id, connection_id)


@router.get("/platform-connections/{connection_id}/sync-events", response_model=PlatformSyncEventListResponse)
async def list_platform_sync_events_endpoint(
    connection_id: uuid.UUID,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    event_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    items, total = await list_platform_sync_events(
        session=session,
        user_id=user_id,
        connection_id=connection_id,
        offset=offset,
        limit=limit,
        event_type=event_type,
        status=status,
    )
    return PlatformSyncEventListResponse(items=items, total=total)


@router.get("/platform-connections/{connection_id}/sync-metrics", response_model=PlatformSyncMetricsResponse)
async def get_platform_sync_metrics_endpoint(
    connection_id: uuid.UUID,
    window_hours: int = Query(default=24, ge=1, le=168),
    session: AsyncSession = Depends(get_session),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    metrics = await get_platform_sync_metrics(
        session=session,
        user_id=user_id,
        connection_id=connection_id,
        window_hours=window_hours,
    )
    return PlatformSyncMetricsResponse(**metrics)


@router.post("/platform-connections/oauth/start", response_model=PlatformOAuthStartResponse)
async def start_platform_oauth_endpoint(
    data: PlatformOAuthStartRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    return build_platform_oauth_start(user_id, data)


@router.get("/platform-connections/oauth/callback", response_model=PlatformOAuthCallbackResponse)
async def platform_oauth_callback_endpoint(
    platform: Platform,
    code: str,
    state: str,
    redirect_to_frontend: bool = Query(default=True),
    session: AsyncSession = Depends(get_session),
):
    try:
        conn = await exchange_platform_oauth_callback(
            session=session,
            platform=platform,
            code=code,
            state=state,
        )
        if redirect_to_frontend:
            return RedirectResponse(
                url=_oauth_redirect_url(
                    status="success",
                    platform=conn.platform.value,
                    region=conn.region,
                    message="OAuth connection established",
                )
            )
        return PlatformOAuthCallbackResponse(
            ok=True,
            platform=conn.platform,
            region=conn.region,
            message="OAuth connection established",
            connection=_to_platform_connection_response(conn),
        )
    except Exception as exc:
        if redirect_to_frontend:
            return RedirectResponse(
                url=_oauth_redirect_url(
                    status="error",
                    platform=platform.value,
                    region="CN",
                    message=str(exc),
                )
            )
        raise
