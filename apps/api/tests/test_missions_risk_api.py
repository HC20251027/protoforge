"""Task 6: Missions + Risk Gate 路由测试。"""
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def test_list_missions_includes_polar_glow(client):
    resp = client.get("/api/missions")
    assert resp.status_code == 200
    data = resp.json()
    ids = {m["id"] for m in data}
    assert "polar-glow-v1" in ids
    polar = next(m for m in data if m["id"] == "polar-glow-v1")
    assert polar["scenario"] == "polar"
    assert len(polar["sliders"]) >= 1
    assert len(polar["risk_rules"]) >= 1


def test_mission_detail_returns_sliders_and_rules(client):
    resp = client.get("/api/missions/polar-glow-v1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["target_cell_line"] == "PolarYeast"
    assert all("key" in s and "default" in s for s in data["sliders"])


def test_mission_404(client):
    resp = client.get("/api/missions/ghost")
    assert resp.status_code == 404


def test_risk_check_all_correct_passes(client):
    mission = client.get("/api/missions/polar-glow-v1").json()
    answers = {r["rule_id"]: r["correct"] for r in mission["risk_rules"]}
    resp = client.post("/api/risk/check", json={"mission_id": "polar-glow-v1", "answers": answers})
    assert resp.status_code == 200
    body = resp.json()
    assert body["passed"] is True
    assert body["score"] == 1.0
    assert all(item["correct"] for item in body["items"])


def test_risk_check_wrong_answer_blocks(client):
    mission = client.get("/api/missions/polar-glow-v1").json()
    wrong = {r["rule_id"]: r["options"][-1] for r in mission["risk_rules"]}
    # 强制确保不是正确选项
    for r in mission["risk_rules"]:
        if wrong[r["rule_id"]] == r["correct"]:
            wrong[r["rule_id"]] = r["options"][0] if r["options"][0] != r["correct"] else r["options"][-1]
    resp = client.post("/api/risk/check", json={"mission_id": "polar-glow-v1", "answers": wrong})
    assert resp.status_code == 200
    body = resp.json()
    assert body["passed"] is False
    assert any(not item["correct"] for item in body["items"])


def test_risk_check_unknown_mission_404(client):
    resp = client.post("/api/risk/check", json={"mission_id": "ghost", "answers": {}})
    assert resp.status_code == 404
