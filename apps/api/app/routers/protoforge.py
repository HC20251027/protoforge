"""ProtoForge 路由(Phase 3 Task 5):Steam 创意工坊上传队列 + 导出文件列表。

路由清单(前缀 `/api/protoforge`):
- GET  /queue                          返回某玩家的待上传队列(pending + failed)
- POST /queue/retry                    触发一次重试所有 pending
- POST /queue/{queue_id}/cancel        取消某条
- GET  /exports                        返回某玩家已打包的 .protoforge 文件列表
"""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

from app.protoforge.packager import list_exports
from app.protoforge.queue import (
    UploadQueue,
)
from app.protoforge.steam import get_default_uploader
from app.schemas import (
    ExportItemSchema,
    ExportListResponse,
    QueueCancelRequest,
    QueueCancelResponse,
    QueueListResponse,
    QueueRetryResponse,
    QueuedItemSchema,
)

log = logging.getLogger("protoforge.router")

router = APIRouter(prefix="/api/protoforge", tags=["protoforge"])


_SAFE_ID_CHARS = set(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-."
)


def _validate_player_id(player_id: str) -> str:
    if not player_id:
        raise HTTPException(status_code=400, detail="player_id 不能为空")
    if not all(c in _SAFE_ID_CHARS for c in player_id):
        raise HTTPException(
            status_code=400, detail="player_id 只能包含字母数字下划线连字符点"
        )
    if len(player_id) > 64:
        raise HTTPException(status_code=400, detail="player_id 过长(>64)")
    return player_id


def _to_schema(item) -> QueuedItemSchema:
    return QueuedItemSchema(
        queue_id=item.queue_id,
        mission_id=item.mission_id,
        ritual=item.ritual,
        status=item.status,
        workshop_id=item.workshop_id,
        error=item.error,
        attempts=item.attempts,
        enqueued_at=item.enqueued_at,
        updated_at=item.updated_at,
        export_path=item.export_path,
    )


# ---------------------------------------------------------------------------
# 队列
# ---------------------------------------------------------------------------


@router.get("/queue", response_model=QueueListResponse)
def list_queue(
    player_id: str = Query(..., description="玩家 ID"),
) -> QueueListResponse:
    """返回某玩家的待上传队列(pending + failed)。"""
    player_id = _validate_player_id(player_id)
    q = UploadQueue.for_player(player_id)
    items = q.list_pending()
    return QueueListResponse(
        items=[_to_schema(it) for it in items],
        pending_count=len(items),
    )


@router.post("/queue/retry", response_model=QueueRetryResponse)
def retry_queue(
    player_id: str = Query(..., description="玩家 ID"),
) -> QueueRetryResponse:
    """触发一次重试所有 pending(联网后玩家点/主菜单自动调)。

    行为:
    - pending 项 → 尝试 upload_item
    - uploaded → 计数
    - failed(原) → 重试
    - cancelled → 跳过

    Returns:
        QueueRetryResponse(attempted, uploaded, failed, skipped)
    """
    player_id = _validate_player_id(player_id)
    q = UploadQueue.for_player(player_id)
    uploader = get_default_uploader()
    pending = q.list_pending()

    attempted = 0
    uploaded = 0
    failed = 0
    skipped = 0

    # 先看 Steam 跑没跑(只在跑的时候才重试,没跑直接跳过 — 留给下次)
    if not uploader.is_steam_running():
        log.info("Steam 未运行,retry 全部跳过(下次再来)")
        return QueueRetryResponse(
            attempted=0,
            uploaded=0,
            failed=0,
            skipped=len(pending),
        )

    for it in pending:
        attempted += 1
        export_path = Path(it.export_path)
        if not export_path.exists():
            # 导出文件丢了 → 标 failed
            q.mark_failed(it.queue_id, error=f"export file missing: {it.export_path}")
            failed += 1
            continue
        try:
            title = f"{it.mission_id} · {it.ritual} · 玩家作品"
            description = (
                f"ProtoForge 玩家作品 (queue_id={it.queue_id})\n"
                f"由 ProtoForge Phase 3 自动生成"
            )
            tags = ["protoforge", f"ritual-{it.ritual}", it.mission_id]
            workshop_id = uploader.upload_item(
                file_path=export_path,
                title=title,
                description=description,
                tags=tags,
            )
            q.mark_uploaded(it.queue_id, workshop_id=workshop_id)
            uploaded += 1
        except Exception as exc:  # noqa: BLE001
            log.warning("retry 上传失败 queue_id=%s: %s", it.queue_id, exc)
            q.mark_failed(it.queue_id, error=str(exc))
            failed += 1

    return QueueRetryResponse(
        attempted=attempted,
        uploaded=uploaded,
        failed=failed,
        skipped=skipped,
    )


@router.post("/queue/{queue_id}/cancel", response_model=QueueCancelResponse)
def cancel_queue_item(
    queue_id: str,
    body: QueueCancelRequest,
) -> QueueCancelResponse:
    """取消某条(玩家主动取消)。"""
    player_id = _validate_player_id(body.player_id)
    q = UploadQueue.for_player(player_id)
    it = q.get(queue_id)
    if it is None:
        raise HTTPException(status_code=404, detail=f"queue_id not found: {queue_id}")
    if it.player_id != player_id:
        raise HTTPException(status_code=403, detail="queue_id 不属于该玩家")
    q.cancel(queue_id)
    return QueueCancelResponse(ok=True, queue_id=queue_id)


# ---------------------------------------------------------------------------
# 导出文件
# ---------------------------------------------------------------------------


@router.get("/exports", response_model=ExportListResponse)
def list_export_files(
    player_id: str = Query(..., description="玩家 ID"),
) -> ExportListResponse:
    """返回某玩家已打包的 .protoforge 文件列表(给 /exports 页面用)。"""
    player_id = _validate_player_id(player_id)
    raw = list_exports(player_id)
    items = [
        ExportItemSchema(
            filename=d["filename"],
            path=d["path"],
            size_bytes=d["size_bytes"],
            mtime=d["mtime"],
            manifest=d["manifest"],
        )
        for d in raw
    ]
    return ExportListResponse(items=items, total=len(items))


__all__ = ["router"]
