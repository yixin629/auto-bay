import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.modules.products.models import Product, ProductStatus
from app.modules.products.schemas import ProductCreate, ProductUpdate


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
