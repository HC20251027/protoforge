"""Ritual 运行状态持久化(Phase 3 Task 3)。

存储策略:JSON 文件(不引 SQLite — Phase 1 已经为 gallery 用了 SQLite,
这里 ritual_state 走 JSON 更轻,文件锁也更简单)。

* 数据目录: `<project_root>/.protoforge/ritual_state/`(在项目根,**不**在 C 盘)
* 每个 run 一个 JSON 文件: `<run_id>.json`
* 玩家重启应用时调 `evaluate_exit_on_return(run_id)` → 自动 evaluate exit

支持的 run 状态:
* `running` — 计算中
* `done`    — 计算完成 + result 已存
* `lost`    — 玩家退出时没算完,标记为 lost(供前端"上次未完成的锻造"列表展示)
"""
from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .exit_penalty import (
    DEFAULT_POLICY,
    ExitOutcome,
    ExitPenaltyPolicy,
    evaluate_exit,
)
from .ritual import get_ritual


# ---------------------------------------------------------------------------
# 数据类
# ---------------------------------------------------------------------------

_RUN_STATUS_RUNNING = "running"
_RUN_STATUS_DONE = "done"
_RUN_STATUS_LOST = "lost"


def _utcnow_iso() -> str:
    """UTC 时间,ISO 格式(便于 JSON 序列化)。"""
    return datetime.now(timezone.utc).isoformat()


@dataclass
class RitualRunState:
    """单次 ritual 运行的完整状态(可序列化)。"""

    run_id: str
    ritual: str
    total_steps: int
    current_step: int
    started_at: str
    last_updated_at: str
    status: str = _RUN_STATUS_RUNNING  # running / done / lost
    fasta_preview: Optional[str] = None  # 断点续传预留
    result: Optional[dict] = None  # complete() 时存

    def progress_ratio(self) -> float:
        """当前进度比例(0.0-1.0)。"""
        if self.total_steps <= 0:
            return 0.0
        return max(0.0, min(1.0, self.current_step / self.total_steps))


# ---------------------------------------------------------------------------
# 存储
# ---------------------------------------------------------------------------

class RitualStateStore:
    """Ritual 状态持久化(JSON 文件)。

    数据目录默认: `<project_root>/.protoforge/ritual_state/`
    显式传入 root 用于测试。
    """

    def __init__(self, root: Optional[Path] = None) -> None:
        if root is None:
            # 默认走项目根目录 .protoforge/ritual_state/
            # apps/api/app/proto/ritual_state.py → parents[3] = project_root
            project_root = Path(__file__).resolve().parents[3]
            root = project_root / ".protoforge" / "ritual_state"
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    # ---------- 路径辅助 ----------

    def _path_for(self, run_id: str) -> Path:
        return self.root / f"{run_id}.json"

    # ---------- CRUD ----------

    def start(self, ritual: str) -> RitualRunState:
        """开炉:生成 run_id,存初始状态。"""
        spec = get_ritual(ritual)
        now = _utcnow_iso()
        run_id = f"run_{uuid.uuid4().hex[:16]}"
        state = RitualRunState(
            run_id=run_id,
            ritual=spec.name.value,
            total_steps=spec.calculation_steps,
            current_step=0,
            started_at=now,
            last_updated_at=now,
            status=_RUN_STATUS_RUNNING,
        )
        self._save(state)
        return state

    def update(self, run_id: str, current_step: int) -> RitualRunState:
        """更新进度(current_step)。current_step 用 int。"""
        state = self.get(run_id)
        if state is None:
            raise KeyError(f"run_id not found: {run_id}")
        # 容错:current_step 不能越界/为负
        if current_step < 0:
            current_step = 0
        if current_step > state.total_steps:
            current_step = state.total_steps
        state.current_step = current_step
        state.last_updated_at = _utcnow_iso()
        self._save(state)
        return state

    def get(self, run_id: str) -> Optional[RitualRunState]:
        """读 run 状态(不存在返回 None)。"""
        path = self._path_for(run_id)
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return RitualRunState(**data)

    def complete(self, run_id: str, result_json: dict) -> None:
        """标完成 + 存 result dict。"""
        state = self.get(run_id)
        if state is None:
            raise KeyError(f"run_id not found: {run_id}")
        state.status = _RUN_STATUS_DONE
        # 标完成时 current_step 推进到 total(确保 evaluate 是 KEEP)
        if state.current_step < state.total_steps:
            state.current_step = state.total_steps
        state.result = result_json
        state.last_updated_at = _utcnow_iso()
        self._save(state)

    def evaluate_exit_on_return(
        self,
        run_id: str,
        policy: ExitPenaltyPolicy = DEFAULT_POLICY,
    ) -> ExitOutcome:
        """玩家重启应用时调用,自动 evaluate exit 并把状态标为 lost(如果是 LOSE)。

        Returns:
            ExitOutcome.KEEP_RESULT / ExitOutcome.LOSE_RESULT
        """
        state = self.get(run_id)
        if state is None:
            return ExitOutcome.LOSE_RESULT
        # 已经 done 的保持 done
        if state.status == _RUN_STATUS_DONE:
            return ExitOutcome.KEEP_RESULT
        outcome = evaluate_exit(state.current_step, state.total_steps, policy)
        if outcome == ExitOutcome.LOSE_RESULT:
            state.status = _RUN_STATUS_LOST
            state.last_updated_at = _utcnow_iso()
            self._save(state)
        return outcome

    def list_unfinished(self) -> list[RitualRunState]:
        """列出所有未完成的 run(running + lost)。"""
        if not self.root.exists():
            return []
        items: list[RitualRunState] = []
        for path in sorted(self.root.glob("run_*.json")):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                state = RitualRunState(**data)
                if state.status != _RUN_STATUS_DONE:
                    items.append(state)
            except (json.JSONDecodeError, TypeError, OSError):
                # 文件损坏 → 跳过(不污染列表)
                continue
        # 最新的在前
        items.sort(key=lambda s: s.started_at, reverse=True)
        return items

    # ---------- 内部 ----------

    def _save(self, state: RitualRunState) -> None:
        path = self._path_for(state.run_id)
        tmp = path.with_suffix(".json.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(asdict(state), f, ensure_ascii=False, indent=2)
        # 原子替换(避免写到一半断电)
        tmp.replace(path)


# ---------------------------------------------------------------------------
# 单例(default root 走项目根)
# ---------------------------------------------------------------------------

_default_store: Optional[RitualStateStore] = None


def get_default_store() -> RitualStateStore:
    """单例 getter(给 router 用)。"""
    global _default_store
    if _default_store is None:
        _default_store = RitualStateStore()
    return _default_store


def reset_default_store() -> None:
    """重置单例(测试用)。"""
    global _default_store
    _default_store = None


__all__ = [
    "RitualRunState",
    "RitualStateStore",
    "get_default_store",
    "reset_default_store",
]
