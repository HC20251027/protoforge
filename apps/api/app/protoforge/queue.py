"""离线待上传队列(Phase 3 Task 5)。

**核心场景**:玩家通关后服务端自动尝试上传到 Steam Workshop;
- Steam 客户端没运行 → 入队,联网后前端调 `POST /queue/retry` 重试
- 网络断 → 入队
- 上传成功 → 标记 uploaded,前端可忽略

持久化策略:**每个玩家一个 JSON 文件**(类似 ritual_state.py):
- 路径:`apps/api/data/upload_queue/{player_id}.json`
- 结构:`list[QueuedItem]`
- 跨进程安全(本任务只走单进程 FastAPI 同步 router;Phase 4 接 async 时再加锁)

**状态机**:
    pending ─(upload_item 成功)─> uploaded
    pending ─(upload_item 失败)─> failed(保留在队列,可重试)
    pending ─(cancel)─────────> cancelled
    uploaded/failed  → 玩家可手动清理
"""
from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


# ---------------------------------------------------------------------------
# 状态常量
# ---------------------------------------------------------------------------

STATUS_PENDING = "pending"
STATUS_UPLOADED = "uploaded"
STATUS_FAILED = "failed"
STATUS_CANCELLED = "cancelled"
# 队列视角:Steam 没运行,玩家"待重试"也属于 pending(status 同 pending,
# 语义层面用 schema 的 "queued"/"uploaded"/"failed" 区分)
STATUS_QUEUED = "queued"  # 适配层给前端的语义状态名(queue.py 内部仍用 pending)

# 默认最多保留多少条历史项(避免 JSON 无限增长)
_MAX_HISTORY = 200


# ---------------------------------------------------------------------------
# 数据类
# ---------------------------------------------------------------------------


@dataclass
class QueuedItem:
    """队列里的一项作品。"""

    queue_id: str
    export_path: str  # 绝对路径(给 steam.py 用)
    mission_id: str
    ritual: str
    player_id: str
    status: str = STATUS_PENDING
    workshop_id: Optional[str] = None  # upload 成功后填
    error: Optional[str] = None  # 失败原因
    attempts: int = 0
    enqueued_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "QueuedItem":
        # 兼容老字段(没有就填默认值)
        return cls(
            queue_id=d["queue_id"],
            export_path=d["export_path"],
            mission_id=d["mission_id"],
            ritual=d["ritual"],
            player_id=d["player_id"],
            status=d.get("status", STATUS_PENDING),
            workshop_id=d.get("workshop_id"),
            error=d.get("error"),
            attempts=int(d.get("attempts", 0)),
            enqueued_at=d.get("enqueued_at", ""),
            updated_at=d.get("updated_at", ""),
        )


# ---------------------------------------------------------------------------
# 工具
# ---------------------------------------------------------------------------


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# 主体:UploadQueue
# ---------------------------------------------------------------------------


class UploadQueue:
    """单玩家的待上传队列(JSON 文件持久化)。

    使用方式:
        q = UploadQueue.for_player("alice")
        qid = q.enqueue(Path(".../xxx.protoforge"), "polar-glow-v1", "urgent")
        items = q.list_pending()
        q.mark_uploaded(qid, workshop_id="mock_xxx")
    """

    def __init__(self, player_id: str, queue_root: Optional[Path] = None) -> None:
        if not player_id or not all(c.isalnum() or c in "_-." for c in player_id):
            raise ValueError(
                f"player_id 非法(只允许字母数字 _-.): {player_id!r}"
            )
        self.player_id = player_id
        if queue_root is None:
            # 默认走 settings.data_dir/upload_queue/(测试可 monkeypatch)
            from app.config import settings  # 局部 import 避免循环依赖

            queue_root = Path(settings.data_dir) / "upload_queue"
        self.queue_root = Path(queue_root)
        self.queue_root.mkdir(parents=True, exist_ok=True)
        self._path = self.queue_root / f"{player_id}.json"

    # ---------- 工厂方法 ----------

    @classmethod
    def for_player(cls, player_id: str, queue_root: Optional[Path] = None) -> "UploadQueue":
        return cls(player_id, queue_root)

    # ---------- 文件 IO ----------

    def _load_raw(self) -> list[dict[str, Any]]:
        if not self._path.exists():
            return []
        try:
            text = self._path.read_text(encoding="utf-8")
            data = json.loads(text)
            if not isinstance(data, list):
                return []
            return data
        except (OSError, json.JSONDecodeError):
            # 文件损坏 → 视为空(不抛 — 队列丢了不影响业务)
            return []

    def _save_raw(self, items: list[QueuedItem]) -> None:
        # 限制历史长度(避免 JSON 无限增长)
        if len(items) > _MAX_HISTORY:
            # 保留最新 _MAX_HISTORY 条
            items = items[-int(_MAX_HISTORY) :]
        tmp = self._path.with_suffix(self._path.suffix + ".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(
                [it.to_dict() for it in items],
                f,
                ensure_ascii=False,
                indent=2,
            )
        # 原子替换
        tmp.replace(self._path)

    def _all_items(self) -> list[QueuedItem]:
        return [QueuedItem.from_dict(d) for d in self._load_raw()]

    # ---------- 公开接口 ----------

    def enqueue(
        self,
        export_path: Path,
        mission_id: str,
        ritual: str,
    ) -> str:
        """入队一项待上传作品,返回 queue_id。

        Args:
            export_path: 已生成的 .protoforge 文件路径(必须是已存在的文件)
            mission_id: 任务 ID
            ritual: 仪式档位
        """
        export_path = Path(export_path)
        if not export_path.exists():
            raise FileNotFoundError(
                f"export file not found: {export_path}"
            )

        now = _utcnow_iso()
        item = QueuedItem(
            queue_id=f"qu_{uuid.uuid4().hex[:16]}",
            export_path=str(export_path.resolve()),
            mission_id=mission_id,
            ritual=ritual,
            player_id=self.player_id,
            status=STATUS_PENDING,
            enqueued_at=now,
            updated_at=now,
        )

        items = self._all_items()
        items.append(item)
        self._save_raw(items)
        return item.queue_id

    def peek(self) -> list[QueuedItem]:
        """返回所有项(给前端显示"待上传 N 个"用,只算 pending + failed)。

        注意:这个方法返回所有项,调用方自己过滤 status。
        或者直接用 list_pending() / list_all()。
        """
        return self._all_items()

    def list_pending(self) -> list[QueuedItem]:
        """返回待上传(pending) + 失败可重试(failed)的项。"""
        return [
            it
            for it in self._all_items()
            if it.status in (STATUS_PENDING, STATUS_FAILED)
        ]

    def list_all(self) -> list[QueuedItem]:
        """返回所有项(包含 uploaded / cancelled) — 给 /exports 调试用。"""
        return self._all_items()

    def mark_uploaded(self, queue_id: str, workshop_id: str) -> None:
        """标记为已上传成功(workshop_id 必填)。"""
        items = self._all_items()
        now = _utcnow_iso()
        found = False
        for it in items:
            if it.queue_id == queue_id:
                it.status = STATUS_UPLOADED
                it.workshop_id = workshop_id
                it.error = None
                it.attempts = it.attempts + 1
                it.updated_at = now
                found = True
                break
        if not found:
            raise KeyError(f"queue_id not found: {queue_id}")
        self._save_raw(items)

    def mark_failed(self, queue_id: str, error: str) -> None:
        """标记为失败(保留在队列,可重试)。

        失败次数 +1,但不重置 status(让它保持 failed,前端 retry 时再切回 pending)。
        """
        items = self._all_items()
        now = _utcnow_iso()
        found = False
        for it in items:
            if it.queue_id == queue_id:
                it.status = STATUS_FAILED
                it.error = error
                it.attempts = it.attempts + 1
                it.updated_at = now
                found = True
                break
        if not found:
            raise KeyError(f"queue_id not found: {queue_id}")
        self._save_raw(items)

    def cancel(self, queue_id: str) -> None:
        """取消(玩家主动取消排队)。"""
        items = self._all_items()
        now = _utcnow_iso()
        found = False
        for it in items:
            if it.queue_id == queue_id:
                it.status = STATUS_CANCELLED
                it.updated_at = now
                found = True
                break
        if not found:
            raise KeyError(f"queue_id not found: {queue_id}")
        self._save_raw(items)

    def get(self, queue_id: str) -> Optional[QueuedItem]:
        """查单项(不存在返回 None)。"""
        for it in self._all_items():
            if it.queue_id == queue_id:
                return it
        return None

    def pending_count(self) -> int:
        """待上传数量(给前端 badge 用)。"""
        return len(self.list_pending())


# ---------------------------------------------------------------------------
# 工厂:批量
# ---------------------------------------------------------------------------


def queue_for(player_id: str, queue_root: Optional[Path] = None) -> UploadQueue:
    """便捷工厂(避免每次都写 UploadQueue.for_player)。"""
    return UploadQueue.for_player(player_id, queue_root)


__all__ = [
    "QueuedItem",
    "UploadQueue",
    "STATUS_PENDING",
    "STATUS_UPLOADED",
    "STATUS_FAILED",
    "STATUS_CANCELLED",
    "STATUS_QUEUED",
    "queue_for",
]
