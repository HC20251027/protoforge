"""Phase 3 Task 2:4 档难度落地测试。

验证 4 档(RitualSpec)在 4 个核心维度(枚举值/字段/get_ritual/engine 集成)上
都符合设计文档 §4.2:
  * 急锻    urgent     1★  2-5s    50 steps   4 cards
  * 主锻    standard   2★  30-120s 200 steps   6 cards
  * 古法锻  ancient    3★  300-900s 800 steps   8 cards
  * 晶种培育 crystal    4★  1800-7200s 3000 steps 12 cards
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.proto.engine import run_forge, run_polar_glow
from app.proto.ritual import (
    ANCIENT_FORGE,
    CRYSTAL_CULTIVATION,
    RITUALS,
    STANDARD_FORGE,
    URGENT_FORGE,
    Ritual,
    default_ritual,
    get_ritual,
)
from app.schemas import ForgeRequest


# ---------------------------------------------------------------------------
# 1. 4 个 RitualSpec 的字段值正确(数据驱动)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "spec,expected_name,expected_difficulty,expected_min,expected_max,expected_steps,expected_cards,expected_badge",
    [
        (URGENT_FORGE, "urgent", 1, 2, 5, 50, 4, "急锻者"),
        (STANDARD_FORGE, "standard", 2, 30, 120, 200, 6, "主锻匠"),
        (ANCIENT_FORGE, "ancient", 3, 300, 900, 800, 8, "古法锻师"),
        (CRYSTAL_CULTIVATION, "crystal", 4, 1800, 7200, 3000, 12, "晶种培育师"),
    ],
)
def test_ritual_spec_fields(
    spec, expected_name, expected_difficulty, expected_min, expected_max,
    expected_steps, expected_cards, expected_badge,
) -> None:
    assert spec.name.value == expected_name
    assert spec.difficulty == expected_difficulty
    assert spec.min_duration_sec == expected_min
    assert spec.max_duration_sec == expected_max
    assert spec.calculation_steps == expected_steps
    assert spec.cards_complexity == expected_cards
    assert spec.badge == expected_badge


# ---------------------------------------------------------------------------
# 2. 4 档中英文名匹配
# ---------------------------------------------------------------------------

def test_ritual_display_names() -> None:
    assert URGENT_FORGE.display_name == "急锻"
    assert STANDARD_FORGE.display_name == "主锻"
    assert ANCIENT_FORGE.display_name == "古法锻"
    assert CRYSTAL_CULTIVATION.display_name == "晶种培育"


# ---------------------------------------------------------------------------
# 3. RITUALS 字典完整(枚举 → spec)
# ---------------------------------------------------------------------------

def test_rituals_dict_complete() -> None:
    assert len(RITUALS) == 4
    assert RITUALS[Ritual.urgent] is URGENT_FORGE
    assert RITUALS[Ritual.standard] is STANDARD_FORGE
    assert RITUALS[Ritual.ancient] is ANCIENT_FORGE
    assert RITUALS[Ritual.crystal] is CRYSTAL_CULTIVATION


# ---------------------------------------------------------------------------
# 4. get_ritual 字符串 → spec
# ---------------------------------------------------------------------------

def test_get_ritual_urgent() -> None:
    assert get_ritual("urgent") is URGENT_FORGE


def test_get_ritual_crystal() -> None:
    assert get_ritual("crystal") is CRYSTAL_CULTIVATION


def test_get_ritual_case_insensitive() -> None:
    """大小写不敏感(防御性 API,前端可能传 ANCIENT)。"""
    assert get_ritual("ANCIENT") is ANCIENT_FORGE
    assert get_ritual("Standard") is STANDARD_FORGE


# ---------------------------------------------------------------------------
# 5. get_ritual 非法值 → ValueError
# ---------------------------------------------------------------------------

def test_get_ritual_invalid_raises() -> None:
    with pytest.raises(ValueError) as exc_info:
        get_ritual("invalid_ritual")
    assert "Unknown ritual" in str(exc_info.value)
    # 错误消息应列出合法值
    assert "urgent" in str(exc_info.value)
    assert "crystal" in str(exc_info.value)


def test_get_ritual_non_string_raises() -> None:
    with pytest.raises(ValueError):
        get_ritual(42)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# 6. default_ritual 返回急锻
# ---------------------------------------------------------------------------

def test_default_ritual_is_urgent() -> None:
    spec = default_ritual()
    assert spec is URGENT_FORGE
    assert spec.name is Ritual.urgent


# ---------------------------------------------------------------------------
# 7. engine.run_forge 接收 ritual 参数并使用 spec.calculation_steps
# ---------------------------------------------------------------------------

def test_run_forge_uses_ritual_steps_ancient() -> None:
    """古法锻档(800 steps)→ MCMC 步数应是 800(用 mcmc_steps=1 路径无法验证,
    所以这里用 monkeypatch 探测 _mcmc_search 的调用)。"""
    captured = {}

    original_search = __import__(
        "app.proto.engine", fromlist=["_mcmc_search"]
    )._mcmc_search

    def spy(length, generator, seed, steps, params):
        captured["steps"] = steps
        return original_search(length, generator, seed, steps, params)

    import app.proto.engine as engine_mod
    engine_mod._mcmc_search = spy
    try:
        run_forge(
            "polar-glow-v1",
            params={"min_target_splice": 0.5, "max_off_target": 0.3},
            generator="preference",
            seed=42,
            ritual="ancient",
        )
    finally:
        engine_mod._mcmc_search = original_search

    assert captured["steps"] == ANCIENT_FORGE.calculation_steps == 800


def test_run_forge_uses_ritual_steps_crystal() -> None:
    """晶种培育档(3000 steps)→ MCMC 步数应是 3000。"""
    captured = {}

    original_search = __import__(
        "app.proto.engine", fromlist=["_mcmc_search"]
    )._mcmc_search

    def spy(length, generator, seed, steps, params):
        captured["steps"] = steps
        return original_search(length, generator, seed, steps, params)

    import app.proto.engine as engine_mod
    engine_mod._mcmc_search = spy
    try:
        run_forge(
            "polar-glow-v1",
            params={"min_target_splice": 0.5, "max_off_target": 0.3},
            generator="preference",
            seed=42,
            ritual="crystal",
        )
    finally:
        engine_mod._mcmc_search = original_search

    assert captured["steps"] == CRYSTAL_CULTIVATION.calculation_steps == 3000


def test_run_forge_default_ritual_is_urgent() -> None:
    """不传 ritual → 走急锻(50 steps)。"""
    captured = {}

    original_search = __import__(
        "app.proto.engine", fromlist=["_mcmc_search"]
    )._mcmc_search

    def spy(length, generator, seed, steps, params):
        captured["steps"] = steps
        return original_search(length, generator, seed, steps, params)

    import app.proto.engine as engine_mod
    engine_mod._mcmc_search = spy
    try:
        run_forge(
            "polar-glow-v1",
            params={"min_target_splice": 0.5, "max_off_target": 0.3},
            generator="preference",
            seed=42,
        )
    finally:
        engine_mod._mcmc_search = original_search

    assert captured["steps"] == URGENT_FORGE.calculation_steps == 50


def test_run_forge_returns_ritual_used_and_estimate() -> None:
    """result 应包含 ritual_used / duration_estimate_sec / badge_unlocked。"""
    result = run_forge(
        "polar-glow-v1",
        params={"min_target_splice": 0.5, "max_off_target": 0.3},
        generator="preference",
        seed=42,
        ritual="standard",
    )
    assert result.ritual == "standard"
    assert result.ritual_used == "standard"
    assert result.duration_estimate_sec == STANDARD_FORGE.max_duration_sec == 120
    assert result.badge_unlocked == "主锻匠"


def test_run_forge_invalid_ritual_raises() -> None:
    """非法 ritual 名应抛 ValueError(get_ritual 的契约)。"""
    with pytest.raises(ValueError):
        run_forge(
            "polar-glow-v1",
            params={},
            generator="preference",
            ritual="bogus",
        )


def test_run_polar_glow_accepts_ritual() -> None:
    """run_polar_glow 也支持 ritual 参数(向后兼容 + 新增)。"""
    result = run_polar_glow(
        params={"min_target_splice": 0.5, "max_off_target": 0.3},
        ritual="ancient",
    )
    assert result.ritual_used == "ancient"
    assert result.badge_unlocked == "古法锻师"


# ---------------------------------------------------------------------------
# 8. Schemas:ForgeRequest 接受 ritual
# ---------------------------------------------------------------------------

def test_forge_request_accepts_ritual_crystal() -> None:
    req = ForgeRequest(mission_id="polar-glow-v1", ritual="crystal")
    assert req.ritual == "crystal"


def test_forge_request_default_ritual_is_urgent() -> None:
    req = ForgeRequest(mission_id="polar-glow-v1")
    assert req.ritual == "urgent"


def test_forge_request_rejects_unknown_ritual() -> None:
    """Pydantic Literal 校验应拒绝未知 ritual。"""
    with pytest.raises(Exception):  # ValidationError
        ForgeRequest(mission_id="polar-glow-v1", ritual="bogus")


# ---------------------------------------------------------------------------
# 9. HTTP /api/forge/run 接受 ritual 字段
# ---------------------------------------------------------------------------

@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def test_api_forge_run_with_crystal_ritual(client: TestClient) -> None:
    """HTTP 端到端:crystal 档位应该返回正确的 duration_estimate_sec。"""
    body = {
        "mission_id": "polar-glow-v1",
        "params": {"min_target_splice": 0.5, "max_off_target": 0.3},
        "generator": "preference",
        "seed": 1,
        "ritual": "crystal",
    }
    resp = client.post("/api/forge/run", json=body)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["ritual"] == "crystal"
    assert data["ritual_used"] == "crystal"
    assert data["duration_estimate_sec"] == 7200
    assert data["badge_unlocked"] == "晶种培育师"


def test_api_forge_run_default_ritual_is_urgent(client: TestClient) -> None:
    """不传 ritual → 默认急锻。"""
    body = {
        "mission_id": "polar-glow-v1",
        "params": {"min_target_splice": 0.5, "max_off_target": 0.3},
        "generator": "preference",
        "seed": 1,
    }
    resp = client.post("/api/forge/run", json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert data["ritual"] == "urgent"
    assert data["duration_estimate_sec"] == 5
    assert data["badge_unlocked"] == "急锻者"


def test_api_ritual_recommend_returns_urgent(client: TestClient) -> None:
    """/ritual/recommend 固定返回急锻(不再按硬件)。"""
    resp = client.get("/api/forge/ritual/recommend")
    assert resp.status_code == 200
    assert resp.json()["ritual"] == "urgent"


def test_api_ritual_list_has_all_four(client: TestClient) -> None:
    """/ritual 列表应包含 4 档(urg/standard/ancient/crystal)。"""
    resp = client.get("/api/forge/ritual")
    assert resp.status_code == 200
    names = {r["ritual"] for r in resp.json()}
    assert names == {"urgent", "standard", "ancient", "crystal"}
