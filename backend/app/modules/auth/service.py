import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError, UnauthorizedError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from app.modules.auth.models import User
from app.modules.auth.schemas import LoginRequest, RegisterRequest, TokenResponse


def _default_preferences() -> dict:
    return {
        "sync_monitor": {
            "success_rate_threshold": 95,
            "consecutive_error_threshold": 3,
            "seven_day_error_rate_threshold": 20,
            "stale_threshold_minutes": 120,
            "auto_refresh_seconds": 60,
        }
    }


async def register_user(session: AsyncSession, data: RegisterRequest) -> User:
    existing = await session.execute(select(User).where(User.email == data.email))
    if existing.scalar_one_or_none():
        raise ConflictError("Email already registered")

    user = User(
        email=data.email,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
    )
    session.add(user)
    await session.flush()
    return user


async def authenticate_user(session: AsyncSession, data: LoginRequest) -> TokenResponse:
    result = await session.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(data.password, user.hashed_password):
        raise UnauthorizedError("Invalid email or password")

    if not user.is_active:
        raise UnauthorizedError("Account is disabled")

    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


async def get_user_preferences(session: AsyncSession, user_id: uuid.UUID) -> dict:
    user = await session.get(User, user_id)
    if not user:
        raise NotFoundError("User not found")

    defaults = _default_preferences()
    current = user.preferences or {}
    sync_monitor = {
        **defaults["sync_monitor"],
        **(current.get("sync_monitor") or {}),
    }
    return {"sync_monitor": sync_monitor}


async def update_user_preferences(session: AsyncSession, user_id: uuid.UUID, payload: dict) -> dict:
    user = await session.get(User, user_id)
    if not user:
        raise NotFoundError("User not found")

    defaults = _default_preferences()
    current = user.preferences or {}
    incoming_sync = (payload.get("sync_monitor") or {})
    merged = {
        "sync_monitor": {
            **defaults["sync_monitor"],
            **(current.get("sync_monitor") or {}),
            **incoming_sync,
        }
    }
    user.preferences = merged
    await session.flush()
    return merged
