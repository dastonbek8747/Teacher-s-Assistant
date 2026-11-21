"""JWT token yaratish va tekshirish."""
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from backend.config import settings


def create_access_token(subject: str | int, expires_minutes: int | None = None) -> str:
    """Foydalanuvchi uchun JWT access token yaratadi."""
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload: dict[str, Any] = {"sub": str(subject), "exp": expire, "iat": datetime.now(timezone.utc)}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Tokenni dekodlaydi. Noto'g'ri yoki muddati o'tgan bo'lsa `jwt.PyJWTError` ko'taradi."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
