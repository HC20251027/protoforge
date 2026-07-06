"""FastAPI 入口。"""
from __future__ import annotations
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import api_router
from app.config import settings
from app import __version__

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("protoforge")

app = FastAPI(
    title="ProtoForge API",
    version=__version__,
    description="ProtoForge Python sidecar - wraps proto-language and scoring models.",
)

# CORS(只允许本地 Tauri WebView 和开发态 Vite)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:1420",       # Tauri 默认 dev 端口
        "http://localhost:5173",       # Vite dev
        "tauri://localhost",
        "http://tauri.localhost",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.on_event("startup")
async def _startup() -> None:
    log.info("ProtoForge API %s starting on %s:%d", __version__, settings.host, settings.port)
    log.info("Data dir: %s", settings.data_dir)
    log.info("Proto profile: %s", settings.proto_profile)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=False)
