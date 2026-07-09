"""Phase 3 Task 3:退出惩罚测试。

覆盖:
* ExitOutcome / ExitPenaltyPolicy
* evaluate_exit 边界(80% / 79% / 100% / 0%)
* evaluate_exit_from_ritual(4 档都生效,晶体 80 步只到 2.7% → LOSE)
* _format_for_ui 永远返回固定字符串(**不**包含百分比)
* RitualStateStore.start/update/get/complete/list_unfinished
* evaluate_exit_on_return 端到端(KEEP / LOSE)
* HTTP `/api/forge/unfinished` 返回 JSON
* HTTP `/api/forge/exit-evaluate` 接受 run_id

至少 15 个测试 — 跑通后 123 → 138 passed。
"""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Iterator

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.proto.engine import run_forge, run_polar_glow
from app.proto.exit_penalty import (
    DEFAULT_POLICY,
    ExitOutcome,
    ExitPenaltyPolicy,
    _format_for_ui,
    evaluate_exit,
    evaluate_exit_from_ritual,
)
from app.proto.ritual import (
    ANCIENT_FORGE,
    CRYSTAL_CULTIVATION,
    STANDARD_FORGE,
    URGENT_FORGE,
)
from app.proto.ritual_state import (
    RitualRunState,
    RitualStateStore,
    get_default_store,
    reset_default_store,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def tmp_store(tmp_path) -> Iterator[RitualStateStore]:
    """临时目录的 store(每个测试一个)。"""
    store = RitualStateStore(root=tmp_path / "ritual_state")
    yield store
    # 不需要清理 — tmp_path 自动删


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


# ---------------------------------------------------------------------------
# 1. ExitOutcome + ExitPenaltyPolicy 基础
# ---------------------------------------------------------------------------

def test_default_policy_keep_threshold_is_80_percent() -> None:
    """默认策略是 80%。"""
    assert DEFAULT_POLICY.keep_threshold == 0.8


def test_exit_outcome_enum_values() -> None:
    """ExitOutcome 是字符串枚举,值是 keep / lose。"""
    assert ExitOutcome.KEEP_RESULT.value == "keep"
    assert ExitOutcome.LOSE_RESULT.value == "lose"


# ---------------------------------------------------------------------------
# 2. evaluate_exit 边界
# ---------------------------------------------------------------------------

def test_evaluate_exit_full_progress_keeps() -> None:
    """100% 进度 → KEEP。"""
    assert evaluate_exit(50, 50) == ExitOutcome.KEEP_RESULT
    assert evaluate_exit(100, 100) == ExitOutcome.KEEP_RESULT


def test_evaluate_exit_exactly_80_percent_keeps() -> None:
    """正好 80% → KEEP(>= 边界)。"""
    assert evaluate_exit(40, 50) == ExitOutcome.KEEP_RESULT
    assert evaluate_exit(80, 100) == ExitOutcome.KEEP_RESULT


def test_evaluate_exit_just_under_80_percent_loses() -> None:
    """79% / 78% → LOSE。"""
    assert evaluate_exit(39, 50) == ExitOutcome.LOSE_RESULT
    assert evaluate_exit(79, 100) == ExitOutcome.LOSE_RESULT


def test_evaluate_exit_zero_progress_loses() -> None:
    """0 进度 → LOSE。"""
    assert evaluate_exit(0, 50) == ExitOutcome.LOSE_RESULT
    assert evaluate_exit(0, 1000) == ExitOutcome.LOSE_RESULT


def test_evaluate_exit_custom_policy() -> None:
    """自定义策略生效(50% 阈值 → 40/50 KEEP,20/50 LOSE)。"""
    policy = ExitPenaltyPolicy(keep_threshold=0.5)
    assert evaluate_exit(40, 50, policy) == ExitOutcome.KEEP_RESULT
    assert evaluate_exit(20, 50, policy) == ExitOutcome.LOSE_RESULT


def test_evaluate_exit_defensive_zero_total_loses() -> None:
    """total_steps <= 0 → LOSE(防御性)。"""
    assert evaluate_exit(50, 0) == ExitOutcome.LOSE_RESULT
    assert evaluate_exit(50, -1) == ExitOutcome.LOSE_RESULT


def test_evaluate_exit_negative_step_clamped() -> None:
    """负 current_step 视作 0(防御性)。"""
    assert evaluate_exit(-5, 100) == ExitOutcome.LOSE_RESULT


# ---------------------------------------------------------------------------
# 3. evaluate_exit_from_ritual(4 档都生效)
# ---------------------------------------------------------------------------

def test_evaluate_exit_from_ritual_ancient_80_steps_keeps() -> None:
    """ancient 档 800 步 → 80 步是 10% → LOSE;640 步是 80% → KEEP。"""
    assert evaluate_exit_from_ritual(80, "ancient") == ExitOutcome.LOSE_RESULT
    assert evaluate_exit_from_ritual(640, "ancient") == ExitOutcome.KEEP_RESULT


def test_evaluate_exit_from_ritual_crystal_loses_at_80_steps() -> None:
    """crystal 档 3000 步 → 80 步是 2.7% → 一定 LOSE(用户需求里的关键例子)。"""
    assert evaluate_exit_from_ritual(80, "crystal") == ExitOutcome.LOSE_RESULT


def test_evaluate_exit_from_ritual_crystal_keeps_at_2400() -> None:
    """crystal 档 3000 步 → 2400 步是 80% → KEEP。"""
    assert evaluate_exit_from_ritual(2400, "crystal") == ExitOutcome.KEEP_RESULT


def test_evaluate_exit_from_ritual_urgent_keeps_at_40() -> None:
    """urgent 档 50 步 → 40 步是 80% → KEEP。"""
    assert evaluate_exit_from_ritual(40, "urgent") == ExitOutcome.KEEP_RESULT


def test_evaluate_exit_from_ritual_standard_keeps_at_160() -> None:
    """standard 档 200 步 → 160 步是 80% → KEEP。"""
    assert evaluate_exit_from_ritual(160, "standard") == ExitOutcome.KEEP_RESULT


# ---------------------------------------------------------------------------
# 4. _format_for_ui 永远返回固定字符串(不暴露百分比)
# ---------------------------------------------------------------------------

def test_format_for_ui_always_returns_fixed_banner() -> None:
    """两种 outcome 都返回同一个固定字符串。"""
    keep_msg = _format_for_ui(ExitOutcome.KEEP_RESULT)
    lose_msg = _format_for_ui(ExitOutcome.LOSE_RESULT)
    assert keep_msg == lose_msg
    assert keep_msg == "⚠️ 锻造中退出游戏会有概率失败"


def test_format_for_ui_does_not_leak_percent() -> None:
    """固定字符串里**不**包含百分比数字。"""
    msg = _format_for_ui(ExitOutcome.LOSE_RESULT)
    # 拒绝任何形如 "X%" 的子串
    assert "%" not in msg
    # 也不应有 "80" / "0.8" 等具体阈值泄漏
    for forbidden in ["80%", "0.8", "80 ", "0.8 ", "百分之"]:
        assert forbidden not in msg


# ---------------------------------------------------------------------------
# 5. RitualStateStore CRUD
# ---------------------------------------------------------------------------

def test_state_store_start_creates_file(tmp_store: RitualStateStore) -> None:
    """start 会创建 JSON 文件并返回 RitualRunState。"""
    state = tmp_store.start("urgent")
    assert state.run_id.startswith("run_")
    assert state.ritual == "urgent"
    assert state.total_steps == URGENT_FORGE.calculation_steps
    assert state.current_step == 0
    assert state.status == "running"
    assert tmp_store._path_for(state.run_id).exists()


def test_state_store_update_writes_progress(tmp_store: RitualStateStore) -> None:
    """update 写 current_step 持久化。"""
    state = tmp_store.start("ancient")
    updated = tmp_store.update(state.run_id, 400)
    assert updated.current_step == 400
    # 重新 get 确认落盘
    again = tmp_store.get(state.run_id)
    assert again is not None
    assert again.current_step == 400


def test_state_store_get_returns_none_for_unknown(tmp_store: RitualStateStore) -> None:
    """未知 run_id → None。"""
    assert tmp_store.get("run_does_not_exist") is None


def test_state_store_complete_marks_done(tmp_store: RitualStateStore) -> None:
    """complete 标 done + 存 result dict。"""
    state = tmp_store.start("urgent")
    tmp_store.update(state.run_id, 50)  # 全部完成
    tmp_store.complete(state.run_id, {"intron": "GTATGCAG", "primary": 0.7})
    again = tmp_store.get(state.run_id)
    assert again is not None
    assert again.status == "done"
    assert again.current_step == again.total_steps  # complete 会推到 total
    assert again.result is not None
    assert again.result["intron"] == "GTATGCAG"


def test_state_store_list_unfinished_filters_done(tmp_store: RitualStateStore) -> None:
    """list_unfinished 不包含 done 的。"""
    a = tmp_store.start("urgent")
    b = tmp_store.start("ancient")
    tmp_store.complete(a.run_id, {})
    unfinished = tmp_store.list_unfinished()
    ids = {s.run_id for s in unfinished}
    assert b.run_id in ids
    assert a.run_id not in ids


def test_state_store_update_clamps_to_total(tmp_store: RitualStateStore) -> None:
    """update 时 current_step > total → 钳到 total。"""
    state = tmp_store.start("urgent")
    updated = tmp_store.update(state.run_id, 99999)
    assert updated.current_step == state.total_steps


# ---------------------------------------------------------------------------
# 6. evaluate_exit_on_return 端到端
# ---------------------------------------------------------------------------

def test_evaluate_exit_on_return_keep(tmp_store: RitualStateStore) -> None:
    """start → update 80% → evaluate → KEEP(标完成)。"""
    state = tmp_store.start("ancient")  # 800 steps
    tmp_store.update(state.run_id, 700)  # 87.5% → KEEP
    outcome = tmp_store.evaluate_exit_on_return(state.run_id)
    assert outcome == ExitOutcome.KEEP_RESULT
    again = tmp_store.get(state.run_id)
    # KEEP 不标 lost,状态保持 running(等玩家来取)
    assert again is not None
    assert again.status != "lost"


def test_evaluate_exit_on_return_lose(tmp_store: RitualStateStore) -> None:
    """start → update 10% → evaluate → LOSE(标 lost)。"""
    state = tmp_store.start("ancient")  # 800 steps
    tmp_store.update(state.run_id, 80)  # 10%
    outcome = tmp_store.evaluate_exit_on_return(state.run_id)
    assert outcome == ExitOutcome.LOSE_RESULT
    again = tmp_store.get(state.run_id)
    assert again is not None
    assert again.status == "lost"


def test_evaluate_exit_on_return_done_always_keeps(tmp_store: RitualStateStore) -> None:
    """已 done 的 run → evaluate 永远 KEEP。"""
    state = tmp_store.start("urgent")
    tmp_store.complete(state.run_id, {})
    outcome = tmp_store.evaluate_exit_on_return(state.run_id)
    assert outcome == ExitOutcome.KEEP_RESULT


def test_evaluate_exit_on_return_unknown_loses(tmp_store: RitualStateStore) -> None:
    """未知 run_id → LOSE(防御性)。"""
    outcome = tmp_store.evaluate_exit_on_return("run_nonexistent")
    assert outcome == ExitOutcome.LOSE_RESULT


# ---------------------------------------------------------------------------
# 7. engine.run_forge 集成(走 tmp store)
# ---------------------------------------------------------------------------

def test_run_forge_uses_run_id_from_state_store(tmp_store: RitualStateStore) -> None:
    """run_forge 走 state_store 时,返回的 run_id 来自 store.start。"""
    result = run_forge(
        "polar-glow-v1",
        params={"min_target_splice": 0.5, "max_off_target": 0.3},
        generator="preference",
        seed=42,
        ritual="urgent",
        state_store=tmp_store,
    )
    # run_id 是 uuid 格式 run_<16hex>
    assert result.run_id.startswith("run_")
    assert len(result.run_id) > len("run_")
    # state 已标 done
    state = tmp_store.get(result.run_id)
    assert state is not None
    assert state.status == "done"


# ---------------------------------------------------------------------------
# 8. HTTP /api/forge/unfinished + /api/forge/exit-evaluate
# ---------------------------------------------------------------------------

def test_api_unfinished_returns_empty_initially(client: TestClient) -> None:
    """/unfinished 至少返回 200 + list(内容取决于全局 store,这里只验 200 + list)。"""
    resp = client.get("/api/forge/unfinished")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_api_unfinished_returns_lost_run(client: TestClient) -> None:
    """unfinished 端点:在 default store 造一个 lost 的 run,验证返回。"""
    # 用 default store 制造一个 lost 的 run
    reset_default_store()
    store = get_default_store()
    state = store.start("urgent")
    store.update(state.run_id, 1)  # 1/50 = 2%
    store.evaluate_exit_on_return(state.run_id)  # 标 lost
    try:
        resp = client.get("/api/forge/unfinished")
        assert resp.status_code == 200
        items = resp.json()
        assert isinstance(items, list)
        # 找到我们刚造的 run
        ids = {it["run_id"] for it in items}
        assert state.run_id in ids
        # outcome 应该是 lose
        target = next(it for it in items if it["run_id"] == state.run_id)
        assert target["outcome"] == "lose"
        assert target["ritual"] == "urgent"
        assert target["current_step"] == 1
        assert target["total_steps"] == 50
    finally:
        # 清理:把刚造的文件删了(避免污染后续测试)
        path = store._path_for(state.run_id)
        if path.exists():
            path.unlink()
        reset_default_store()


def test_api_exit_evaluate_404_for_unknown(client: TestClient) -> None:
    """exit-evaluate 对未知 run_id 返回 404。"""
    resp = client.post("/api/forge/exit-evaluate", json={"run_id": "run_does_not_exist"})
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"]


def test_api_exit_evaluate_returns_outcome(client: TestClient) -> None:
    """exit-evaluate 返回 outcome + progress_ratio。"""
    reset_default_store()
    store = get_default_store()
    state = store.start("ancient")  # 800 steps
    store.update(state.run_id, 80)  # 10% → LOSE
    try:
        resp = client.post("/api/forge/exit-evaluate", json={"run_id": state.run_id})
        assert resp.status_code == 200
        data = resp.json()
        assert data["outcome"] == "lose"
        assert data["ritual"] == "ancient"
        # progress_ratio = 80/800 = 0.1
        assert data["progress_ratio"] == pytest.approx(0.1, abs=0.01)
    finally:
        path = store._path_for(state.run_id)
        if path.exists():
            path.unlink()
        reset_default_store()
