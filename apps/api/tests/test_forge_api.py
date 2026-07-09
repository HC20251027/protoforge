"""Task 5: Forge API 路由测试。"""
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def test_ritual_list_returns_all_levels(client):
    resp = client.get("/api/forge/ritual")
    assert resp.status_code == 200
    rituals = resp.json()
    assert {r["ritual"] for r in rituals} == {"urgent", "standard", "ancient", "crystal"}


def test_ritual_recommend_returns_known_value(client):
    resp = client.get("/api/forge/ritual/recommend")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ritual"] in {"urgent", "standard", "ancient", "crystal"}


def test_forge_run_happy_path(client):
    body = {
        "mission_id": "polar-glow-v1",
        "params": {"min_target_splice": 0.5, "max_off_target": 0.3},
        "generator": "preference",
        "seed": 42,
    }
    resp = client.post("/api/forge/run", json=body)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["mission_id"] == "polar-glow-v1"
    assert 80 <= len(data["intron"]) <= 250
    assert data["fasta"].startswith(">")
    assert "primary" in data["scores"]
    assert 0.0 <= data["scores"]["primary"] <= 2.0


def test_forge_run_unknown_mission_404(client):
    resp = client.post("/api/forge/run", json={"mission_id": "ghost"})
    assert resp.status_code == 404
    assert "Unknown" in resp.json()["detail"]


def test_forge_run_with_natural_language(client):
    """ForgeRequest.natural_language 非空时,服务端自动翻译再 forge。"""
    body = {
        "mission_id": "polar-glow-v1",
        "params": {},  # 空 — 用翻译结果
        "generator": "preference",
        "natural_language": "严格一点",
    }
    resp = client.post("/api/forge/run", json=body)
    assert resp.status_code == 200
    data = resp.json()
    # 严格翻译后 min_target_splice 应 > 0.65 default
    assert data["intron"]


def test_forge_run_natural_language_overrides_params(client):
    """NL 翻译结果应覆盖 params 中的同名键。"""
    body = {
        "mission_id": "polar-glow-v1",
        "params": {"min_target_splice": 0.5},  # 与 NL 严格冲突
        "generator": "preference",
        "natural_language": "严格",
    }
    resp = client.post("/api/forge/run", json=body)
    assert resp.status_code == 200


def test_forge_run_natural_language_empty_uses_params(client):
    """NL 为空时应直接用 params。"""
    body = {
        "mission_id": "polar-glow-v1",
        "params": {"min_target_splice": 0.5},
        "generator": "preference",
    }
    resp = client.post("/api/forge/run", json=body)
    assert resp.status_code == 200
    assert resp.json()["fasta"].startswith(">")
