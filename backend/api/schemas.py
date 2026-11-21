"""Pydantic sxemalari (request/response modellari)."""
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class UserCreate(BaseModel):
    """Ro'yxatdan o'tish so'rovi."""

    username: str = Field(min_length=3, max_length=50, examples=["ustoz_ali"])
    email: EmailStr = Field(examples=["ali@example.com"])
    password: str = Field(min_length=8, max_length=128, examples=["StrongPass123"])
    confirm_password: str = Field(min_length=8, max_length=128, examples=["StrongPass123"])

    @model_validator(mode="after")
    def passwords_match(self):
        if self.password != self.confirm_password:
            raise ValueError("Parollar mos kelmadi (passwords don't match)")
        return self


class UserLogin(BaseModel):
    """Tizimga kirish so'rovi."""

    username: str = Field(examples=["ustoz_ali"])
    password: str = Field(examples=["StrongPass123"])


class UserOut(BaseModel):
    """Foydalanuvchi haqida ochiq ma'lumot."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: EmailStr
    created_at: datetime


class Token(BaseModel):
    """JWT javobi."""

    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int


class TokenData(BaseModel):
    username: Optional[str] = None


# ---------------------------------------------------------------------------
# Chat / Agents
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    """Chat so'rovi."""

    message: str = Field(
        min_length=1,
        examples=["Bugun 7-A sinfga informatika dars rejasini tayyorla"],
    )
    session_id: Optional[str] = Field(
        default=None,
        description="Suhbat sessiyasi ID. Berilmasa avtomatik yaratiladi.",
    )


class ChatResponse(BaseModel):
    """Chat javobi."""

    session_id: str
    response: str
    approved: bool = False
    attempts: int = 0
    next_agent: Optional[str] = None
    raw: Optional[dict[str, Any]] = None


class AgentInfo(BaseModel):
    """Mavjud agent haqida ma'lumot."""

    key: str
    node: str
    description: str


class HealthResponse(BaseModel):
    status: str
    version: str
    database: str


# Eski nomlar bilan moslik uchun
CreateUSer = UserCreate
LoginUser = UserLogin
