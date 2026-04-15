import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user_id, get_session
from app.modules.pricing.service import (
    calculate_cost_plus_price,
    get_exchange_rate,
)

router = APIRouter()


class PriceCalculationRequest(BaseModel):
    base_cost: Decimal
    cost_currency: str = "CNY"
    target_currency: str = "AUD"
    margin_pct: Decimal = Decimal("0.30")
    platform: str = "ebay"
    shipping_estimate: Decimal = Decimal("0")


class PriceCalculationResponse(BaseModel):
    suggested_price: Decimal
    exchange_rate: Decimal
    cost_in_target: Decimal
    estimated_profit: Decimal
    margin_pct: Decimal


@router.post("/calculate", response_model=PriceCalculationResponse)
async def calculate_price(
    data: PriceCalculationRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    rate = await get_exchange_rate(session, data.cost_currency, data.target_currency)
    cost_in_target = data.base_cost * rate
    price = calculate_cost_plus_price(
        data.base_cost,
        data.cost_currency,
        data.target_currency,
        rate,
        data.margin_pct,
        data.platform,
        data.shipping_estimate,
    )
    profit = price - cost_in_target - data.shipping_estimate
    return PriceCalculationResponse(
        suggested_price=price,
        exchange_rate=rate,
        cost_in_target=cost_in_target.quantize(Decimal("0.01")),
        estimated_profit=profit.quantize(Decimal("0.01")),
        margin_pct=data.margin_pct,
    )
