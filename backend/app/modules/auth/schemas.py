import uuid

from pydantic import BaseModel, EmailStr


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str | None
    role: str
    is_active: bool

    model_config = {"from_attributes": True}


class SyncMonitorPreferences(BaseModel):
    success_rate_threshold: int = 95
    consecutive_error_threshold: int = 3
    seven_day_error_rate_threshold: int = 20
    stale_threshold_minutes: int = 120
    auto_refresh_seconds: int = 60


class UserPreferencesResponse(BaseModel):
    sync_monitor: SyncMonitorPreferences


class UserPreferencesUpdateRequest(BaseModel):
    sync_monitor: SyncMonitorPreferences
