"""Phase 3 Task 6 P0-A2:run_forge 显式失败 — 不再静默退化。

修复前:`run_forge` 内部如果 MCMC 步骤抛错,会把异常"消化"成默认
score=0 + intron="" 的占位 result,玩家看不出"算法没找到好序列"和
"算法崩了"的区别。

修复后:内层错误包成 `ForgeExecutionError`,顶层 catch 后:
1. `result.errors: list[str]` 非空(带错误信息)
2. `result.passed_gate = False`
3. `result.intron = ""` (不返回假数据)
4. HTTP 仍 200(玩家能继续),前端按 errors 是否非空决定要不要显示横幅
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.proto import engine
from app.proto.engine import run_forge, run_polar_glow, ForgeResult


# ---------------------------------------------------------------------------
# 后端单测
# ---------------------------------------------------------------------------

def test_run_forge_happy_path_has_empty_errors():
    """正常路径下 errors 应为空(向后兼容,旧 154 个测试不感知 errors)。"""
    result = run_polar_glow(params={"min_target_splice": 0.5})
    assert result.errors == []
    assert result.passed_gate in (True, False)  # 取决于 seed,关键是 errors 为空


def test_run_forge_records_error_on_mcmc_failure(monkeypatch):
    """MCMC 步骤抛错时,result.errors 应非空 + passed_gate=False + intron=""。"""
    def boom(*args, **kwargs):
        raise RuntimeError("MCMC kernel panic: divergent chain")

    # 强制让 _mcmc_search 抛错(monkeypatch 替换函数对象)
    monkeypatch.setattr(engine, "_mcmc_search", boom)

    result = run_forge(
        "polar-glow-v1",
        params={"mcmc_steps": 10},
        generator="preference",
        seed=42,
    )

    # 错误已记录
    assert len(result.errors) >= 1
    assert any("MCMC" in e for e in result.errors)
    assert any("RuntimeError" in e for e in result.errors)
    assert any("MCMC kernel panic" in e for e in result.errors)
    # passed_gate 必须是 False(没有静默通过)
    assert result.passed_gate is False
    # intron 应是空(不能返回假数据)
    assert result.intron == ""
    # 所有 components 应是 0(默认占位,不是某个假的高分)
    components = result.scores["components"]
    assert components["target_splice"] == 0.0
    assert components["orthogonality"] == 0.0
    assert components["gc_penalty"] == 0.0
    assert components["length_penalty"] == 0.0


def test_run_forge_failure_does_not_silently_pass_gate(monkeypatch):
    """失败时 passed_gate 必然是 False,玩家不可能因为 bug 误以为通关。"""
    def boom(*args, **kwargs):
        raise ValueError("constraint violation: min_target_splice out of range")

    monkeypatch.setattr(engine, "_mcmc_search", boom)
    result = run_forge("polar-glow-v1", params={"mcmc_steps": 5}, generator="uniform", seed=1)
    assert result.passed_gate is False


def test_run_forge_known_mission_template_load_failure():
    """_load_template 抛 ValueError 时,run_forge 仍要抛(这是契约,不是 bug)。
    模板加载失败是 API 层 404 处理的事,run_forge 内部不 catch。
    """
    with pytest.raises(ValueError, match="Unknown mission_id"):
        run_forge("ghost-mission", params={}, generator="preference", seed=42)


# ---------------------------------------------------------------------------
# 路由层测试:HTTP 仍 200 返回,errors 通过 schema 透传给前端
# ---------------------------------------------------------------------------

@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def test_forge_run_api_returns_errors_field(client, monkeypatch):
    """POST /api/forge/run 响应里 errors 字段存在 + 失败时非空。"""
    from app.proto import engine

    def boom(*args, **kwargs):
        raise RuntimeError("chain diverged at step 7")

    monkeypatch.setattr(engine, "_mcmc_search", boom)

    resp = client.post(
        "/api/forge/run",
        json={
            "mission_id": "polar-glow-v1",
            "params": {"mcmc_steps": 10},
            "generator": "preference",
            "seed": 42,
        },
    )
    # HTTP 仍 200(玩家能继续,不被 bug 卡死)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    # errors 字段存在
    assert "errors" in body
    assert isinstance(body["errors"], list)
    assert len(body["errors"]) >= 1
    # 错误信息可读
    assert any("chain diverged at step 7" in e for e in body["errors"])
    # passed_gate 必须 False
    assert body["passed_gate"] is False


def test_forge_run_api_happy_path_has_empty_errors(client):
    """正常路径下 errors 字段为空列表(向后兼容,前端不会显示错误横幅)。"""
    resp = client.post(
        "/api/forge/run",
        json={
            "mission_id": "polar-glow-v1",
            "params": {"min_target_splice": 0.5, "max_off_target": 0.3},
            "generator": "preference",
            "seed": 42,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("errors") == []
