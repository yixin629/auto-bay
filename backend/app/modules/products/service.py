import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import BadRequestError, ConflictError, ForbiddenError, NotFoundError
from app.core.security import (
    create_oauth_state,
    decode_oauth_state,
    decrypt_credentials,
    encrypt_credentials,
)
from app.integrations.registry import ConnectorRegistry
from app.modules.products.models import Platform, PlatformConnection, PlatformSyncEvent, Product, ProductStatus
from app.modules.products.schemas import (
    PlatformConnectionCreate,
    PlatformConnectionUpdate,
    PlatformOAuthStartRequest,
    PlatformOAuthStartResponse,
    ProductCreate,
    ProductUpdate,
)


def _compute_consecutive_error_count(statuses: list[str]) -> int:
    consecutive_error_count = 0
    for item in statuses:
        if item != "error":
            break
        consecutive_error_count += 1
    return consecutive_error_count


def _build_daily_trend_points(rows: list[dict], days: int, now: datetime) -> list[dict]:
    start_day = (now - timedelta(days=days - 1)).date()

    row_by_day: dict[str, dict] = {}
    for row in rows:
        day_value = row["day"]
        day_key = day_value.date().isoformat() if hasattr(day_value, "date") else str(day_value)
        row_by_day[day_key] = {
            "total_events": int(row.get("total_events") or 0),
            "success_events": int(row.get("success_events") or 0),
            "error_events": int(row.get("error_events") or 0),
            "avg_duration_ms": (
                float(row["avg_duration_ms"]) if row.get("avg_duration_ms") is not None else None
            ),
        }

    points: list[dict] = []
    for idx in range(days):
        day = (start_day + timedelta(days=idx)).isoformat()
        sample = row_by_day.get(
            day,
            {
                "total_events": 0,
                "success_events": 0,
                "error_events": 0,
                "avg_duration_ms": None,
            },
        )
        total_events = int(sample["total_events"])
        success_events = int(sample["success_events"])
        success_rate = (success_events / total_events * 100.0) if total_events > 0 else None

        points.append(
            {
                "day": day,
                "total_events": total_events,
                "success_events": success_events,
                "error_events": int(sample["error_events"]),
                "success_rate": success_rate,
                "avg_duration_ms": sample["avg_duration_ms"],
            }
        )

    return points


async def create_product(
    session: AsyncSession,
    user_id: uuid.UUID,
    data: ProductCreate,
) -> Product:
    """Create a new product owned by the given user.

    Raises ConflictError if the SKU is already taken.
    """
    existing = await session.execute(
        select(Product).where(Product.sku == data.sku)
    )
    if existing.scalar_one_or_none():
        raise ConflictError(f"Product with SKU '{data.sku}' already exists")

    values = data.model_dump()

    # Serialize nested Pydantic models to plain dicts for JSONB storage
    if values.get("dimensions_cm") is not None:
        values["dimensions_cm"] = data.dimensions_cm.model_dump()
    if values.get("images"):
        values["images"] = [img.model_dump() for img in data.images]

    product = Product(user_id=user_id, **values)
    session.add(product)
    await session.flush()
    return product


async def get_product(
    session: AsyncSession,
    user_id: uuid.UUID,
    product_id: uuid.UUID,
) -> Product:
    """Fetch a single product, ensuring it belongs to the requesting user."""
    product = await session.get(Product, product_id)
    if product is None:
        raise NotFoundError("Product not found")
    if product.user_id != user_id:
        raise ForbiddenError("You do not have access to this product")
    return product


async def list_products(
    session: AsyncSession,
    user_id: uuid.UUID,
    offset: int = 0,
    limit: int = 50,
    status_filter: ProductStatus | None = None,
) -> tuple[list[Product], int]:
    """Return a paginated list of the user's products with a total count."""
    base_filter = Product.user_id == user_id
    if status_filter is not None:
        base_filter = base_filter & (Product.status == status_filter)

    # Total count
    count_stmt = select(func.count()).select_from(Product).where(base_filter)
    total = (await session.execute(count_stmt)).scalar_one()

    # Paginated rows ordered by newest first
    rows_stmt = (
        select(Product)
        .where(base_filter)
        .order_by(Product.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await session.execute(rows_stmt)
    products = list(result.scalars().all())

    return products, total


async def update_product(
    session: AsyncSession,
    user_id: uuid.UUID,
    product_id: uuid.UUID,
    data: ProductUpdate,
) -> Product:
    """Partially update a product.

    Only fields explicitly set by the client are written.
    Raises ConflictError if the new SKU collides with another product.
    """
    product = await get_product(session, user_id, product_id)

    update_data = data.model_dump(exclude_unset=True)

    # SKU uniqueness check when the SKU is being changed
    if "sku" in update_data and update_data["sku"] != product.sku:
        existing = await session.execute(
            select(Product).where(Product.sku == update_data["sku"])
        )
        if existing.scalar_one_or_none():
            raise ConflictError(f"Product with SKU '{update_data['sku']}' already exists")

    # Serialize nested Pydantic models for JSONB storage
    if "dimensions_cm" in update_data and update_data["dimensions_cm"] is not None:
        update_data["dimensions_cm"] = data.dimensions_cm.model_dump()
    if "images" in update_data and update_data["images"] is not None:
        update_data["images"] = [img.model_dump() for img in data.images]

    for field, value in update_data.items():
        setattr(product, field, value)

    await session.flush()
    return product


async def delete_product(
    session: AsyncSession,
    user_id: uuid.UUID,
    product_id: uuid.UUID,
) -> None:
    """Hard-delete a product after verifying ownership."""
    product = await get_product(session, user_id, product_id)
    await session.delete(product)
    await session.flush()


async def create_platform_connection(
    session: AsyncSession,
    user_id: uuid.UUID,
    data: PlatformConnectionCreate,
) -> PlatformConnection:
    existing = await session.execute(
        select(PlatformConnection).where(
            PlatformConnection.user_id == user_id,
            PlatformConnection.platform == data.platform,
            PlatformConnection.region == data.region.upper(),
        )
    )
    if existing.scalar_one_or_none():
        raise ConflictError(
            f"Platform connection already exists for {data.platform.value}/{data.region.upper()}"
        )

    conn = PlatformConnection(
        user_id=user_id,
        platform=data.platform,
        region=data.region.upper(),
        account_name=data.account_name,
        credentials=encrypt_credentials(data.credentials),
        is_active=data.is_active,
    )
    session.add(conn)
    await session.flush()
    return conn


async def get_platform_connection(
    session: AsyncSession,
    user_id: uuid.UUID,
    connection_id: uuid.UUID,
) -> PlatformConnection:
    conn = await session.get(PlatformConnection, connection_id)
    if conn is None:
        raise NotFoundError("Platform connection not found")
    if conn.user_id != user_id:
        raise ForbiddenError("You do not have access to this platform connection")
    return conn


async def list_platform_connections(
    session: AsyncSession,
    user_id: uuid.UUID,
    offset: int = 0,
    limit: int = 50,
    platform: Platform | None = None,
) -> tuple[list[PlatformConnection], int]:
    filter_expr = PlatformConnection.user_id == user_id
    if platform is not None:
        filter_expr = filter_expr & (PlatformConnection.platform == platform)

    count_stmt = select(func.count()).select_from(PlatformConnection).where(filter_expr)
    total = (await session.execute(count_stmt)).scalar_one()

    rows_stmt = (
        select(PlatformConnection)
        .where(filter_expr)
        .order_by(PlatformConnection.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await session.execute(rows_stmt)
    return list(result.scalars().all()), total


async def update_platform_connection(
    session: AsyncSession,
    user_id: uuid.UUID,
    connection_id: uuid.UUID,
    data: PlatformConnectionUpdate,
) -> PlatformConnection:
    conn = await get_platform_connection(session, user_id, connection_id)
    update_data = data.model_dump(exclude_unset=True)
    if "credentials" in update_data and update_data["credentials"] is not None:
        update_data["credentials"] = encrypt_credentials(update_data["credentials"])
    for field, value in update_data.items():
        setattr(conn, field, value)

    await session.flush()
    return conn


async def delete_platform_connection(
    session: AsyncSession,
    user_id: uuid.UUID,
    connection_id: uuid.UUID,
) -> None:
    conn = await get_platform_connection(session, user_id, connection_id)
    await session.delete(conn)
    await session.flush()


async def test_platform_connection(
    session: AsyncSession,
    user_id: uuid.UUID,
    connection_id: uuid.UUID,
) -> tuple[Platform, str, bool]:
    conn = await get_platform_connection(session, user_id, connection_id)
    connector = ConnectorRegistry.get_connector(
        conn.platform,
        credentials=decrypt_credentials(conn.credentials),
        region=conn.region,
    )
    ok = await connector.validate_connection()
    return conn.platform, conn.region, ok


def _oauth_platform_config(platform: Platform) -> dict:
    if platform == Platform.DOUYIN:
        return {
            "client_id": settings.douyin_app_id,
            "client_secret": settings.douyin_app_secret,
            "authorize_url": settings.douyin_oauth_authorize_url,
            "token_url": settings.douyin_oauth_token_url,
            "redirect_uri": settings.douyin_oauth_redirect_uri,
            "default_scopes": ["user_info", "video.list"],
        }
    if platform == Platform.XIAOHONGSHU:
        return {
            "client_id": settings.xiaohongshu_app_id,
            "client_secret": settings.xiaohongshu_app_secret,
            "authorize_url": settings.xiaohongshu_oauth_authorize_url,
            "token_url": settings.xiaohongshu_oauth_token_url,
            "redirect_uri": settings.xiaohongshu_oauth_redirect_uri,
            "default_scopes": ["user_info"],
        }
    raise BadRequestError(f"OAuth is not supported for platform: {platform.value}")


def build_platform_oauth_start(
    user_id: uuid.UUID,
    data: PlatformOAuthStartRequest,
) -> PlatformOAuthStartResponse:
    conf = _oauth_platform_config(data.platform)
    if not conf["client_id"] or not conf["client_secret"]:
        raise BadRequestError(
            f"{data.platform.value} OAuth is not configured (missing app credentials)."
        )

    scopes = data.scopes or conf["default_scopes"]
    state_payload = {
        "sub": str(user_id),
        "platform": data.platform.value,
        "region": data.region.upper(),
    }
    state = create_oauth_state(state_payload)

    params = {
        "client_id": conf["client_id"],
        "redirect_uri": conf["redirect_uri"],
        "response_type": "code",
        "scope": " ".join(scopes),
        "state": state,
    }

    auth_url = f"{conf['authorize_url']}?{urlencode(params)}"
    return PlatformOAuthStartResponse(
        platform=data.platform,
        region=data.region.upper(),
        authorization_url=auth_url,
        state=state,
    )


async def exchange_platform_oauth_callback(
    session: AsyncSession,
    platform: Platform,
    code: str,
    state: str,
) -> PlatformConnection:
    state_data = decode_oauth_state(state)
    if not state_data:
        raise BadRequestError("Invalid OAuth state")

    if state_data.get("platform") != platform.value:
        raise BadRequestError("OAuth state does not match platform")

    user_id = state_data.get("sub")
    region = str(state_data.get("region", "CN")).upper()
    if not user_id:
        raise BadRequestError("OAuth state missing user context")

    conf = _oauth_platform_config(platform)
    token_payload = {
        "grant_type": "authorization_code",
        "client_id": conf["client_id"],
        "client_secret": conf["client_secret"],
        "code": code,
        "redirect_uri": conf["redirect_uri"],
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(conf["token_url"], data=token_payload)
            resp.raise_for_status()
            token_data = resp.json()
    except Exception as exc:
        raise BadRequestError(f"OAuth token exchange failed: {exc}") from exc

    credentials = {
        "app_id": conf["client_id"],
        "app_secret": conf["client_secret"],
        "access_token": token_data.get("access_token", ""),
        "refresh_token": token_data.get("refresh_token", ""),
        "expires_in": token_data.get("expires_in"),
        "raw_token": token_data,
    }

    existing = await session.execute(
        select(PlatformConnection).where(
            PlatformConnection.user_id == uuid.UUID(user_id),
            PlatformConnection.platform == platform,
            PlatformConnection.region == region,
        )
    )
    conn = existing.scalar_one_or_none()
    if conn is None:
        conn = PlatformConnection(
            user_id=uuid.UUID(user_id),
            platform=platform,
            region=region,
            account_name=f"{platform.value}-{region}",
            credentials=encrypt_credentials(credentials),
            is_active=True,
        )
        session.add(conn)
        await session.flush()
    else:
        conn.credentials = encrypt_credentials(credentials)
        conn.is_active = True
        await session.flush()

    return conn


async def list_platform_sync_events(
    session: AsyncSession,
    user_id: uuid.UUID,
    connection_id: uuid.UUID,
    offset: int = 0,
    limit: int = 50,
    event_type: str | None = None,
    status: str | None = None,
) -> tuple[list[PlatformSyncEvent], int]:
    conn = await get_platform_connection(session, user_id, connection_id)

    filter_expr = PlatformSyncEvent.platform_connection_id == conn.id
    if event_type:
        filter_expr = filter_expr & (PlatformSyncEvent.event_type == event_type)
    if status:
        filter_expr = filter_expr & (PlatformSyncEvent.status == status)

    count_stmt = select(func.count()).select_from(PlatformSyncEvent).where(filter_expr)
    total = (await session.execute(count_stmt)).scalar_one()

    rows_stmt = (
        select(PlatformSyncEvent)
        .where(filter_expr)
        .order_by(PlatformSyncEvent.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await session.execute(rows_stmt)
    return list(result.scalars().all()), total


async def get_platform_sync_metrics(
    session: AsyncSession,
    user_id: uuid.UUID,
    connection_id: uuid.UUID,
    window_hours: int = 24,
) -> dict:
    conn = await get_platform_connection(session, user_id, connection_id)

    now_utc = datetime.now(timezone.utc)
    window_start = now_utc - timedelta(hours=window_hours)
    base_filter = PlatformSyncEvent.platform_connection_id == conn.id
    window_filter = base_filter & (PlatformSyncEvent.created_at >= window_start)

    summary_stmt = select(
        func.count().label("total_events"),
        func.sum(case((PlatformSyncEvent.status == "success", 1), else_=0)).label("success_events"),
        func.sum(case((PlatformSyncEvent.status == "error", 1), else_=0)).label("error_events"),
        func.avg(PlatformSyncEvent.duration_ms).label("avg_duration_ms"),
    ).where(window_filter)
    summary = (await session.execute(summary_stmt)).one()

    total_events = int(summary.total_events or 0)
    success_events = int(summary.success_events or 0)
    error_events = int(summary.error_events or 0)
    avg_duration_ms = float(summary.avg_duration_ms) if summary.avg_duration_ms is not None else None
    success_rate = (success_events / total_events * 100.0) if total_events > 0 else None

    recent_status_stmt = (
        select(PlatformSyncEvent.status)
        .where(base_filter)
        .order_by(PlatformSyncEvent.created_at.desc())
        .limit(100)
    )
    recent_statuses = list((await session.execute(recent_status_stmt)).scalars().all())
    consecutive_error_count = _compute_consecutive_error_count(recent_statuses)

    last_success_stmt = (
        select(PlatformSyncEvent.created_at)
        .where(base_filter & (PlatformSyncEvent.status == "success"))
        .order_by(PlatformSyncEvent.created_at.desc())
        .limit(1)
    )
    last_error_stmt = (
        select(PlatformSyncEvent.created_at)
        .where(base_filter & (PlatformSyncEvent.status == "error"))
        .order_by(PlatformSyncEvent.created_at.desc())
        .limit(1)
    )
    last_success_at = (await session.execute(last_success_stmt)).scalar_one_or_none()
    last_error_at = (await session.execute(last_error_stmt)).scalar_one_or_none()

    trend_days = 7
    trend_start = now_utc - timedelta(days=trend_days - 1)
    trend_stmt = (
        select(
            func.date_trunc("day", PlatformSyncEvent.created_at).label("day"),
            func.count().label("total_events"),
            func.sum(case((PlatformSyncEvent.status == "success", 1), else_=0)).label("success_events"),
            func.sum(case((PlatformSyncEvent.status == "error", 1), else_=0)).label("error_events"),
            func.avg(PlatformSyncEvent.duration_ms).label("avg_duration_ms"),
        )
        .where(base_filter & (PlatformSyncEvent.created_at >= trend_start))
        .group_by(func.date_trunc("day", PlatformSyncEvent.created_at))
        .order_by(func.date_trunc("day", PlatformSyncEvent.created_at))
    )
    trend_result = await session.execute(trend_stmt)
    trend_rows = [
        {
            "day": row.day,
            "total_events": row.total_events,
            "success_events": row.success_events,
            "error_events": row.error_events,
            "avg_duration_ms": row.avg_duration_ms,
        }
        for row in trend_result
    ]
    daily_trend = _build_daily_trend_points(trend_rows, trend_days, now_utc)

    return {
        "platform_connection_id": conn.id,
        "window_hours": window_hours,
        "total_events": total_events,
        "success_events": success_events,
        "error_events": error_events,
        "success_rate": success_rate,
        "avg_duration_ms": avg_duration_ms,
        "consecutive_error_count": consecutive_error_count,
        "last_success_at": last_success_at,
        "last_error_at": last_error_at,
        "daily_trend": daily_trend,
    }
