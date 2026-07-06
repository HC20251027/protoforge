"""Task 8: Onboarding + LLM provider 路由测试。"""
import pytest
from fastapi.testclient import TestClient

from app import llm
from app.config import settings
from app.main import app


@pytest.fixture(autouse=True)
def _isolated_data_dir(tmp_path, monkeypatch):
    """每个用例把 llm.json 写到 tmp,避免污染真实数据目录。"""
    test_dir = tmp_path / "data"
    test_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(settings, "data_dir", test_dir)
    monkeypatch.setattr(llm, "_CONFIG_PATH", test_dir / "llm.json")
    yield


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def test_status_default_is_disabled(client):
    resp = client.get("/api/onboarding/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["active"] == "disabled"
    assert {p["label"] for p in body["providers"]} >= {
        "云端 API(推荐 DeepSeek / OpenAI 兼容)",
        "本地模型(Ollama / LM Studio)",
        "不使用 LLM(纯滑块模式)",
    }


def test_save_preserves_api_key_when_blank(client):
    # 先保存带 key
    client.post(
        "/api/onboarding/save",
        json={
            "active": "cloud",
            "providers": {
                "cloud": {
                    "base_url": "https://api.deepseek.com/v1",
                    "model": "deepseek-chat",
                    "api_key": "secret-key-1",
                }
            },
        },
    )
    # 再次保存但 api_key 留空 — 应当保留
    body = client.post(
        "/api/onboarding/save",
        json={
            "active": "cloud",
            "providers": {
                "cloud": {
                    "base_url": "https://api.deepseek.com/v1",
                    "model": "deepseek-chat",
                    "api_key": "",
                }
            },
        },
    ).json()
    assert body["active"] == "cloud"
    assert body["config"]["cloud"]["api_key_set"] is True


def test_test_disabled_always_ok(client):
    resp = client.post("/api/onboarding/test", json={"name": "disabled", "config": {}})
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True


def test_test_local_unreachable_returns_error(client, monkeypatch):
    """本地 LLM 未启动时应返回 ok=False + 友好提示。"""

    import httpx

    def _boom(*args, **kwargs):
        raise httpx.ConnectError("simulated: cannot connect")

    monkeypatch.setattr(httpx, "get", _boom)
    resp = client.post(
        "/api/onboarding/test",
        json={"name": "local", "config": {"base_url": "http://127.0.0.1:1/v1", "model": "x"}},
    )
    body = resp.json()
    assert body["ok"] is False
    assert "不可达" in body["message"] or "网络" in body["message"]


def test_reset_returns_defaults(client):
    client.post(
        "/api/onboarding/save",
        json={"active": "local", "providers": {"local": {"base_url": "x", "model": "y"}}},
    )
    body = client.post("/api/onboarding/reset").json()
    assert body["active"] == "disabled"
