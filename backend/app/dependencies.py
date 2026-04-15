import uuid
from collections.abc import AsyncGenerator

import jwt
from fastapi import Depends, Header

from app.config import settings
from app.core.exceptions import UnauthorizedError
from app.db.session import AsyncSession, get_db


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_db():
        yield session


async def get_current_user_id(
    authorization: str = Header(..., alias="Authorization"),
) -> uuid.UUID:
    if not authorization.startswith("Bearer "):
        raise UnauthorizedError("Invalid authorization header")
    token = authorization[7:]
    try:
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
        user_id = payload.get("sub")
        if user_id is None:
            raise UnauthorizedError("Invalid token payload")
        return uuid.UUID(user_id)
    except jwt.ExpiredSignatureError:
        raise UnauthorizedError("Token has expired")
    except (jwt.InvalidTokenError, ValueError):
        raise UnauthorizedError("Invalid token")
