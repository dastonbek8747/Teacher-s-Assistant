"""Application configuration loaded from environment variables.

Barcha sozlamalar `.env` faylidan yoki muhit o'zgaruvchilaridan o'qiladi.
"""
from pathlib import Path
import os

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent

load_dotenv(BASE_DIR / ".env")


def _get_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class Settings:
    PROJECT_NAME: str = os.getenv("PROJECT_NAME", "Ustoz AI — Teacher's Assistant")
    VERSION: str = os.getenv("VERSION", "1.0.0")
    DESCRIPTION: str = (
        "O'qituvchilar uchun ko'p agentli (multi-agent) sun'iy intellekt platformasi. "
        "Supervisor agent foydalanuvchi so'rovini tahlil qilib, uni mos mutaxassis "
        "agentga yo'naltiradi: brauzer, database, document, game, lesson, rag, research."
    )

    API_V1_PREFIX: str = "/api/v1"

    # --- JWT / Auth ---
    SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "CHANGE-ME-IN-PRODUCTION-please-use-a-long-random-string")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

    # --- Database ---
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./teachflow.db")
    CREATE_TABLES_ON_STARTUP: bool = _get_bool("CREATE_TABLES_ON_STARTUP", True)

    # --- CORS ---
    CORS_ORIGINS: list[str] = [
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "*").split(",")
        if origin.strip()
    ]

    # --- Files ---
    STATIC_DIR: Path = BASE_DIR / "creating_files"


settings = Settings()
