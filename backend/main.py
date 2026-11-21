"""Ustoz AI — Teacher's Assistant backend (FastAPI).

Ishga tushirish (repo ildizidan):
    uvicorn backend.main:app --reload --port 8001
"""
from contextlib import asynccontextmanager

from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

try:  # dark-swag o'rnatilgan bo'lsa, chiroyli Swagger UI ishlatiladi
    from dark_swag import FastAPI
except Exception:  # pragma: no cover - oddiy FastAPI'ga qaytamiz
    from fastapi import FastAPI

from backend.api import models  # noqa: F401  (modellarni ro'yxatdan o'tkazish uchun)
from backend.api.db_conn import Base, engine
from backend.api.routes import agents, auth, chat, health
from backend.config import settings


@asynccontextmanager
async def lifespan(app):
    if settings.CREATE_TABLES_ON_STARTUP:
        Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.DESCRIPTION,
    version=settings.VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

settings.STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount(
    "/creating_files",
    StaticFiles(directory=str(settings.STATIC_DIR)),
    name="creating_files",
)

app.include_router(health.router)
app.include_router(health.router, prefix=settings.API_V1_PREFIX)
app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(chat.router, prefix=settings.API_V1_PREFIX)
app.include_router(agents.router, prefix=settings.API_V1_PREFIX)


@app.get("/", tags=["Root"], summary="API haqida ma'lumot")
def index():
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs": "/docs",
        "redoc": "/redoc",
        "api_prefix": settings.API_V1_PREFIX,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host="0.0.0.0", port=8001, reload=True)
