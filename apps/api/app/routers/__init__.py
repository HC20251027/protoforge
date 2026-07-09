"""Router aggregation."""
from fastapi import APIRouter

from .forge import router as forge_router
from .gallery import router as gallery_router
from .health import router as health_router
from .missions import router as missions_router
from .onboarding import router as onboarding_router
from .protoforge import router as protoforge_router
from .risk import router as risk_router
from .translate import router as translate_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(forge_router)
api_router.include_router(missions_router)
api_router.include_router(risk_router)
api_router.include_router(gallery_router)
api_router.include_router(onboarding_router)
api_router.include_router(translate_router)
api_router.include_router(protoforge_router)

__all__ = ["api_router"]
