"""Task 9: Translate 路由 + 启发式/LLM 回退测试。"""
import json

import pytest
from fastapi.testclient import TestClient

from app import llm
from app.config import settings
from app.main import app


@pytest.fixture(autouse=True)
def _isolated_data_dir(tmp_path, monkeypatch):
    test_dir = tmp_path / "data"
    test_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(settings, "data_dir", test_dir)
    monkeypatch.setattr(llm, "_CONFIG_PATH", test_dir / "llm.json")
    yield


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def test_heuristic_strict_increases_thresholds(client):
    resp = client.post(
        "/api/translate",
        json={"mission_id": "polar-glow-v1", "text": "我要严格的方案"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["provider"] == "disabled"
    assert body["values"]["min_target_splice"] > 0.65  # default
    assert body["values"]["max_off_target"] < 0.20  # default


def test_heuristic_loose_relaxes_thresholds(client):
    resp = client.post(
        "/api/translate",
        json={"mission_id": "polar-glow-v1", "text": "随便来点,宽松一点"},
    )
    body = resp.json()
    assert body["values"]["min_target_splice"] < 0.65


def test_heuristic_more_steps_increases_mcmc(client):
    resp = client.post(
        "/api/translate",
        json={"mission_id": "polar-glow-v1", "text": "多算一些,我要更准"},
    )
    body = resp.json()
    assert body["values"]["mcmc_steps"] >= 100


def test_translate_unknown_mission_404(client):
    resp = client.post("/api/translate", json={"mission_id": "ghost", "text": "hi"})
    assert resp.status_code == 404


def test_translate_falls_back_when_llm_fails(client, monkeypatch):
    """active=cloud 但无 api_key → LLM 抛错 → 启发式兜底。"""
    # 先切到 cloud
    client.post(
        "/api/onboarding/save",
        json={
            "active": "cloud",
            "providers": {
                "cloud": {"base_url": "https://api.deepseek.com/v1", "model": "x", "api_key": ""}
            },
        },
    )
    resp = client.post(
        "/api/translate",
        json={"mission_id": "polar-glow-v1", "text": "严格"},
    )
    body = resp.json()
    assert "启发式" in body["explanation"] or "回退" in body["explanation"]
    # 启发式仍应给出 min_target_splice 提升
    assert body["values"]["min_target_splice"] > 0.65


def test_translate_uses_llm_chat(client, monkeypatch):
    """translate 应该走 LLMProvider.chat() 而非自己 httpx。"""
    captured = {"called": False, "messages": None, "temperature": None}

    class FakeProvider:
        name = "cloud"

        def chat(self, messages, temperature=0.2, max_tokens=256, config=None):
            captured["called"] = True
            captured["messages"] = messages
            captured["temperature"] = temperature
            return '{"min_target_splice": 0.9}'

    # 切到 cloud(需要 api_key 才能正常 chat)
    client.post(
        "/api/onboarding/save",
        json={
            "active": "cloud",
            "providers": {
                "cloud": {
                    "base_url": "https://api.deepseek.com/v1",
                    "model": "deepseek-chat",
                    "api_key": "sk-test",
                }
            },
        },
    )
    # monkey patch LLMProvider:把 _PROVIDERS 字典里 "cloud" 键替换为 FakeProvider
    from app.llm import _PROVIDERS

    monkeypatch.setitem(_PROVIDERS, "cloud", FakeProvider())

    resp = client.post(
        "/api/translate",
        json={"mission_id": "polar-glow-v1", "text": "极严"},
    )
    body = resp.json()
    assert captured["called"] is True
    assert body["values"]["min_target_splice"] == 0.9
    assert body["provider"] == "cloud"
