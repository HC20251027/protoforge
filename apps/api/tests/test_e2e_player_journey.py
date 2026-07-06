"""Task 16: 端到端流程测试 — 完整玩家旅程。

模拟流程:
1) 列出 missions
2) 拉取 mission 详情(sliders + risk_rules)
3) 锻造 run
4) 提交风险门判定
5) 落到 gallery(SQLite)
6) 列表 gallery 看到
"""
import pytest
from fastapi.testclient import TestClient

from app import gallery_store
from app.config import settings
from app.main import app


@pytest.fixture(autouse=True)
def _isolated_db(tmp_path, monkeypatch):
    test_dir = tmp_path / "data"
    test_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(settings, "data_dir", test_dir)
    monkeypatch.setattr(settings, "db_path", test_dir / "test.db")
    gallery_store.set_backend("memory")
    gallery_store.reset()
    yield
    gallery_store.reset()


def test_full_player_journey():
    client = TestClient(app)

    # 1) 健康
    r = client.get("/health")
    assert r.status_code == 200

    # 2) 列任务
    missions = client.get("/api/missions").json()
    assert any(m["id"] == "polar-glow-v1" for m in missions)
    detail = client.get("/api/missions/polar-glow-v1").json()

    # 3) 锻造
    forge = client.post(
        "/api/forge/run",
        json={
            "mission_id": "polar-glow-v1",
            "params": {s["key"]: s["default"] for s in detail["sliders"]},
            "generator": "preference",
            "seed": 7,
        },
    )
    assert forge.status_code == 200
    fr = forge.json()
    assert fr["fasta"].startswith(">")

    # 4) 风险门(全对)
    answers = {rule["rule_id"]: rule["correct"] for rule in detail["risk_rules"]}
    risk = client.post(
        "/api/risk/check",
        json={"mission_id": "polar-glow-v1", "answers": answers},
    )
    assert risk.status_code == 200
    rr = risk.json()
    assert rr["passed"] is True

    # 5) 落 gallery
    create = client.post(
        "/api/gallery",
        json={
            "mission_id": fr["mission_id"],
            "title": "E2E run",
            "intron": fr["intron"],
            "fasta": fr["fasta"],
            "scores": fr["scores"],
            "ritual": fr["ritual"],
            "notes": "from e2e",
            "risk_passed": rr["passed"],
        },
    )
    assert create.status_code == 200
    art = create.json()
    assert art["risk_passed"] is True

    # 6) 列表可见
    listing = client.get("/api/gallery").json()
    assert listing["total"] >= 1
    assert any(a["id"] == art["id"] for a in listing["items"])


def test_translate_then_forge_round_trip():
    client = TestClient(app)
    # 用户在 disabled 模式下用 NL 翻译,然后用翻译结果锻造
    tr = client.post(
        "/api/translate",
        json={"mission_id": "polar-glow-v1", "text": "严格一点,确保不要在 HEK293 表达"},
    )
    assert tr.status_code == 200
    values = tr.json()["values"]
    assert values["min_target_splice"] > 0.65

    forge = client.post(
        "/api/forge/run",
        json={
            "mission_id": "polar-glow-v1",
            "params": values,
            "generator": "preference",
            "seed": 1,
        },
    )
    assert forge.status_code == 200
    assert forge.json()["scores"]["primary"] >= 0
