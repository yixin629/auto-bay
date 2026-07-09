import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user_id, get_session
from app.modules.auth.models import User
from app.modules.auth.schemas import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserPreferencesResponse,
    UserPreferencesUpdateRequest,
    UserResponse,
)
from app.modules.auth.service import (
    authenticate_user,
    get_user_preferences,
    register_user,
    update_user_preferences,
)

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(data: RegisterRequest, session: AsyncSession = Depends(get_session)):
    user = await register_user(session, data)
    return user


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, session: AsyncSession = Depends(get_session)):
    return await authenticate_user(session, data)


@router.get("/me", response_model=UserResponse)
async def get_me(
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    user = await session.get(User, user_id)
    if not user:
        from app.core.exceptions import NotFoundError

        raise NotFoundError("User not found")
    return user


@router.get("/me/preferences", response_model=UserPreferencesResponse)
async def get_my_preferences(
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    prefs = await get_user_preferences(session, user_id)
    return UserPreferencesResponse(**prefs)


@router.patch("/me/preferences", response_model=UserPreferencesResponse)
async def update_my_preferences(
    data: UserPreferencesUpdateRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    prefs = await update_user_preferences(session, user_id, data.model_dump())
    return UserPreferencesResponse(**prefs)
