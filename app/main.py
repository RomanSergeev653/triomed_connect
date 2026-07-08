from fastapi import FastAPI

from app.config import settings
from app.routers import api

app = FastAPI(
    title=settings.app_name,
    description="HTTPS-прослойка между amoCRM и MyDenta (FileMaker Data API)",
    version="1.0.0",
)

app.include_router(api.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
