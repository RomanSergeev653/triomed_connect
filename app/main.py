from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import api

app = FastAPI(
    title=settings.app_name,
    description="HTTPS-прослойка между amoCRM и MyDenta (FileMaker Data API)",
    version="1.0.0",
)

# Виджет в браузере ходит с *.amocrm.ru / *.kommo.com — без CORS preflight падает
# (PreflightMissingAllowOriginHeader / OPTIONS 405).
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_origin_regex=settings.cors_allow_origin_regex,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(api.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
