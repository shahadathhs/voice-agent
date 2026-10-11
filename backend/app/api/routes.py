from typing import Any

from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter()


@router.get("/")
async def root() -> dict[str, Any]:
    settings = get_settings()
    return {
        "app_name": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "endpoints": {
            "health": "/health",
            "websocket": "/ws",
        },
    }


@router.get("/health")
async def health() -> dict[str, Any]:
    from app.api.ws import stt

    settings = get_settings()
    return {
        "status": "ok",
        "version": settings.app_version,
        "environment": settings.environment,
        "stt": {
            "model": settings.whisper_model,
            "loaded": stt.loaded,
        },
    }
