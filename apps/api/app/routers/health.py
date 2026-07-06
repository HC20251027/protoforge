"""健康检查端点。"""
from __future__ import annotations
from fastapi import APIRouter
from app.config import settings
from app import __version__

router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "version": __version__,
        "data_dir": str(settings.data_dir),
        "db_path": str(settings.db_path),
        "proto_profile": settings.proto_profile,
    }
