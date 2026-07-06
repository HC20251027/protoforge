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
    assert {r["ritual"] for r in rituals} == {"swift", "standard", "ancient", "crystal"}


def test_ritual_recommend_returns_known_value(client):
    resp = client.get("/api/forge/ritual/recommend")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ritual"] in {"swift", "standard", "ancient", "crystal"}


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
