import base64
import hashlib
import json
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from cryptography.fernet import Fernet, InvalidToken

from app.config import settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.jwt_access_token_expire_minutes)
    )
    payload = {"sub": subject, "exp": expire, "type": "access"}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.jwt_refresh_token_expire_days)
    payload = {"sub": subject, "exp": expire, "type": "refresh"}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])


def create_oauth_state(payload: dict, expires_minutes: int = 10) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    data = {
        **payload,
        "exp": expire,
        "type": "oauth_state",
    }
    return jwt.encode(data, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_oauth_state(token: str) -> dict:
    data = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    if data.get("type") != "oauth_state":
        return {}
    return data


_CREDENTIALS_MARKER = "__encrypted__"


def _credentials_fernet() -> Fernet:
    key_material = settings.credentials_encryption_key or settings.secret_key
    digest = hashlib.sha256(key_material.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_credentials(credentials: dict | None) -> dict:
    payload = credentials or {}
    if not payload:
        return {}
    token = _credentials_fernet().encrypt(
        json.dumps(payload, separators=(",", ":")).encode("utf-8")
    ).decode("utf-8")
    return {_CREDENTIALS_MARKER: token}


def decrypt_credentials(stored: dict | None) -> dict:
    payload = stored or {}
    if not payload:
        return {}

    token = payload.get(_CREDENTIALS_MARKER)
    if token is None:
        # Backward compatibility for rows created before encryption rollout.
        return payload

    try:
        raw = _credentials_fernet().decrypt(token.encode("utf-8"))
        data = json.loads(raw.decode("utf-8"))
        return data if isinstance(data, dict) else {}
    except (InvalidToken, UnicodeDecodeError, json.JSONDecodeError):
        return {}
