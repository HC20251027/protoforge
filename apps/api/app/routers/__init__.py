"""API 路由聚合(占位,后续 task 逐步加 router)。"""
from fastapi import APIRouter
from .health import router as health_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
