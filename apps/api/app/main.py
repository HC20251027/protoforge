"""FastAPI 入口。"""
from __future__ import annotations
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import api_router
from app.routers.vendor import router as vendor_router
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
app.include_router(vendor_router, prefix="/api/vendor", tags=["vendor"])


@app.on_event("startup")
async def _startup() -> None:
    log.info("ProtoForge API %s starting on %s:%d", __version__, settings.host, settings.port)
    log.info("Data dir: %s", settings.data_dir)
    log.info("Proto profile: %s", settings.proto_profile)
    if settings.db_path:
        from app.db import init_db
        try:
            await init_db()
            log.info("DB ready: %s", settings.db_path)
        except Exception as exc:  # noqa: BLE001
            log.warning("DB init failed (continuing with in-memory gallery): %s", exc)
            from app import gallery_store
            gallery_store.set_backend("memory")

    # Phase 3 Task 3:启动时恢复上次未完成的 run(evaluate exit 状态)
    try:
        from app.proto.engine import recover_unfinished_runs
        kept = recover_unfinished_runs()
        if kept:
            log.info("Recovered %d unfinished run(s) on startup (KEEP_RESULT)", len(kept))
    except Exception as exc:  # noqa: BLE001
        # 恢复失败不能阻止启动
        log.warning("recover_unfinished_runs failed (continuing): %s", exc)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=False)
