from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    from app.db.session import engine

    yield
    # Shutdown
    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    _register_routers(app)
    return app


def _register_routers(app: FastAPI) -> None:
    from app.modules.auth.router import router as auth_router
    from app.modules.products.router import router as products_router
    from app.modules.listings.router import router as listings_router
    from app.modules.orders.router import router as orders_router
    from app.modules.inventory.router import router as inventory_router
    from app.modules.pricing.router import router as pricing_router
    from app.modules.customer_service.router import router as cs_router
    from app.modules.marketing.router import router as marketing_router

    prefix = settings.api_v1_prefix
    app.include_router(auth_router, prefix=f"{prefix}/auth", tags=["auth"])
    app.include_router(products_router, prefix=f"{prefix}/products", tags=["products"])
    app.include_router(listings_router, prefix=f"{prefix}/listings", tags=["listings"])
    app.include_router(orders_router, prefix=f"{prefix}/orders", tags=["orders"])
    app.include_router(inventory_router, prefix=f"{prefix}/inventory", tags=["inventory"])
    app.include_router(pricing_router, prefix=f"{prefix}/pricing", tags=["pricing"])
    app.include_router(cs_router, prefix=f"{prefix}/customer-service", tags=["customer-service"])
    app.include_router(marketing_router, prefix=f"{prefix}/marketing", tags=["marketing"])


app = create_app()
