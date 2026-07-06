"""Router aggregation."""
from fastapi import APIRouter

from .forge import router as forge_router
from .health import router as health_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(forge_router)

__all__ = ["api_router"]
