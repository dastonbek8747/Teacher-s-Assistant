"""Autentifikatsiya endpoint'lari: ro'yxatdan o'tish, kirish, profil."""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from backend.api.db_conn import get_db
from backend.api.deps import get_current_user
from backend.api.hashing_password import hash_password, verify_password
from backend.api.models import User
from backend.api.schemas import Token, UserCreate, UserLogin, UserOut
from backend.api.security import create_access_token
from backend.config import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Yangi foydalanuvchi ro'yxatdan o'tkazish",
)
def register(payload: UserCreate, db: Session = Depends(get_db)) -> User:
    exists = db.scalar(
        select(User).where(
            or_(User.username == payload.username, User.email == payload.email)
        )
    )
    if exists:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bu username yoki email allaqachon ro'yxatdan o'tgan",
        )

    user = User(
        username=payload.username,
        email=payload.email,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _authenticate(db: Session, username: str, password: str) -> Token:
    user = db.scalar(select(User).where(User.username == username))
    if user is None or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Username yoki parol noto'g'ri",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Token(
        access_token=create_access_token(user.id),
        expires_in_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
    )


@router.post("/login", response_model=Token, summary="Tizimga kirish (JWT olish)")
def login(payload: UserLogin, db: Session = Depends(get_db)) -> Token:
    return _authenticate(db, payload.username, payload.password)


@router.post(
    "/token",
    response_model=Token,
    summary="OAuth2 form orqali token (Swagger Authorize uchun)",
    include_in_schema=True,
)
def token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> Token:
    return _authenticate(db, form_data.username, form_data.password)


@router.get("/me", response_model=UserOut, summary="Joriy foydalanuvchi profili")
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user
