"""Phase 3 Task 4 — 引导页 3 步配置 /state + /complete 端点测试。

覆盖(>= 10 个 case):
1.  GET /state 默认返回 {completed: false}
2.  POST /complete with cloud + deepseek + 假 key → 落盘成功 + has_api_key=true
3.  POST /complete with cloud 但缺 api_key → 422
4.  POST /complete with cloud 但缺 cloud_provider → 422
5.  POST /complete with local-bundled 但 vendor local_llm 不可用 → 422
6.  POST /complete with local-bundled + vendor 可用 → 成功
7.  POST /complete with disabled → 成功(纯滑块模式)
8.  POST /complete 后 GET /state → completed=true
9.  API key 在落盘文件里 **不** 是明文(grep 找不到原 key 字符串)
10. GET /state 跨 user 隔离(user_b 看不到 user_a 的 completed=true)
11. user_id 路径穿越被挡(空 / ../ / 非法字符)
12. GET /state 返回的 vendor_status 字段稳定
"""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import llm
from app.config import settings
from app.main import app
from app.routers import onboarding as onboarding_mod


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _isolated_data_dir(tmp_path, monkeypatch):
    """每个用例:把 data_dir 指到 tmp,且把 _KEY_PATH 重定向到 tmp。"""
    test_dir = tmp_path / "data"
    test_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(settings, "data_dir", test_dir)
    monkeypatch.setattr(llm, "_CONFIG_PATH", test_dir / "llm.json")
    # _onboarding_dir() 用的是 settings.data_dir,会被上面那条覆盖;
    # _KEY_PATH 在模块 load 时已解析为绝对路径,monkeypatch 到 tmp
    monkeypatch.setattr(onboarding_mod, "_KEY_PATH", test_dir / ".protoforge_key")
    yield


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture()
def fake_vendor_status():
    """默认 vendor 状态:local_llm 不可用。case 6 会覆盖。"""
    return {
        "proto_language": {"available": True, "size_mb": 12, "path": "vendor/proto-language/build/lib"},
        "ml_models": {
            "esm2-150m": {"available": True, "size_mb": 567, "path": "vendor/models/esm2-150m"},
            "spliceai": {"available": False, "size_mb": 0, "path": "vendor/models/spliceai"},
            "splice-transformer": {"available": False, "size_mb": 0, "path": "vendor/models/splice-transformer"},
        },
        "local_llm": {
            "available": False,
            "size_mb": 0,
            "path": "vendor/llm",
            "model_name": "Qwen2.5-7B-Instruct-Q4_K_M",
        },
    }


@pytest.fixture(autouse=True)
def _patch_vendor_status(monkeypatch, fake_vendor_status):
    """默认所有测试都走 fake vendor,避免依赖真实 vendor 文件。"""
    monkeypatch.setattr(onboarding_mod, "_get_vendor_status", lambda: fake_vendor_status)
    yield


# ---------------------------------------------------------------------------
# 1. 默认状态
# ---------------------------------------------------------------------------


def test_state_default_returns_completed_false(client):
    resp = client.get("/api/onboarding/state", params={"user_id": "alice"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["completed"] is False
    assert body["llm_provider"] == "disabled"
    assert body["cloud_provider"] is None
    assert body["has_api_key"] is False
    assert "vendor_status" in body


# ---------------------------------------------------------------------------
# 2. cloud + deepseek + 假 key → 写盘成功
# ---------------------------------------------------------------------------


def test_complete_cloud_deepseek_persists(client, tmp_path, monkeypatch):
    user_id = "alice"
    resp = client.post(
        "/api/onboarding/complete",
        params={"user_id": user_id},
        json={
            "llm_provider": "cloud",
            "cloud_provider": "deepseek",
            "api_key": "sk-test-fake-key-1234567890",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert "欢迎" in body["message"]

    # 落盘文件存在
    onb_dir = Path(settings.data_dir) / "onboarding"
    f = onb_dir / f"{user_id}.json"
    assert f.exists()
    raw = f.read_text(encoding="utf-8")
    assert "sk-test-fake-key-1234567890" not in raw  # 重要:不存明文


# ---------------------------------------------------------------------------
# 3. cloud 缺 api_key → 422
# ---------------------------------------------------------------------------


def test_complete_cloud_missing_api_key_rejected(client):
    resp = client.post(
        "/api/onboarding/complete",
        params={"user_id": "alice"},
        json={"llm_provider": "cloud", "cloud_provider": "deepseek", "api_key": ""},
    )
    assert resp.status_code == 422
    assert "api_key" in resp.text or "云" in resp.text


def test_complete_cloud_missing_api_key_omitted_rejected(client):
    resp = client.post(
        "/api/onboarding/complete",
        params={"user_id": "alice"},
        json={"llm_provider": "cloud", "cloud_provider": "deepseek"},
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# 4. cloud 缺 cloud_provider → 422
# ---------------------------------------------------------------------------


def test_complete_cloud_missing_provider_rejected(client):
    resp = client.post(
        "/api/onboarding/complete",
        params={"user_id": "alice"},
        json={"llm_provider": "cloud", "api_key": "sk-x"},
    )
    assert resp.status_code == 422
    assert "cloud_provider" in resp.text or "云" in resp.text


# ---------------------------------------------------------------------------
# 5. local-bundled 但 vendor 不可用 → 422
# ---------------------------------------------------------------------------


def test_complete_local_bundled_vendor_unavailable_rejected(client):
    # 默认 fake_vendor_status.local_llm.available = False
    resp = client.post(
        "/api/onboarding/complete",
        params={"user_id": "alice"},
        json={"llm_provider": "local-bundled"},
    )
    assert resp.status_code == 422
    assert "local_llm" in resp.text or "vendor" in resp.text


# ---------------------------------------------------------------------------
# 6. local-bundled + vendor 可用 → 成功
# ---------------------------------------------------------------------------


def test_complete_local_bundled_vendor_available_ok(client, monkeypatch):
    # 把 vendor 状态切到 local_llm.available=True
    monkeypatch.setattr(
        onboarding_mod,
        "_get_vendor_status",
        lambda: {
            "proto_language": {"available": True, "size_mb": 12, "path": "x"},
            "ml_models": {},
            "local_llm": {
                "available": True,
                "size_mb": 4466,
                "path": "vendor/llm",
                "model_name": "Qwen2.5-7B-Instruct-Q4_K_M",
            },
        },
    )
    resp = client.post(
        "/api/onboarding/complete",
        params={"user_id": "alice"},
        json={"llm_provider": "local-bundled"},
    )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


# ---------------------------------------------------------------------------
# 7. disabled → 成功
# ---------------------------------------------------------------------------


def test_complete_disabled_ok(client):
    resp = client.post(
        "/api/onboarding/complete",
        params={"user_id": "bob"},
        json={"llm_provider": "disabled"},
    )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
    # 落盘
    f = Path(settings.data_dir) / "onboarding" / "bob.json"
    assert f.exists()


# ---------------------------------------------------------------------------
# 8. POST 之后 GET /state → completed=true
# ---------------------------------------------------------------------------


def test_post_then_get_state_completed(client):
    user_id = "carol"
    client.post(
        "/api/onboarding/complete",
        params={"user_id": user_id},
        json={"llm_provider": "disabled"},
    )
    resp = client.get("/api/onboarding/state", params={"user_id": user_id})
    body = resp.json()
    assert body["completed"] is True
    assert body["llm_provider"] == "disabled"
    assert body["has_api_key"] is False


def test_post_cloud_then_state_has_api_key(client):
    user_id = "dave"
    client.post(
        "/api/onboarding/complete",
        params={"user_id": user_id},
        json={"llm_provider": "cloud", "cloud_provider": "claude", "api_key": "sk-x"},
    )
    resp = client.get("/api/onboarding/state", params={"user_id": user_id})
    body = resp.json()
    assert body["completed"] is True
    assert body["llm_provider"] == "cloud"
    assert body["cloud_provider"] == "claude"
    assert body["has_api_key"] is True


# ---------------------------------------------------------------------------
# 9. 落盘文件 grep 不到明文 key
# ---------------------------------------------------------------------------


def test_api_key_not_stored_in_plaintext(client, tmp_path):
    user_id = "eve"
    secret = "sk-very-secret-key-abcdef-ghijklmnop"
    client.post(
        "/api/onboarding/complete",
        params={"user_id": user_id},
        json={"llm_provider": "cloud", "cloud_provider": "openai", "api_key": secret},
    )
    f = Path(settings.data_dir) / "onboarding" / f"{user_id}.json"
    assert f.exists()
    text = f.read_text(encoding="utf-8")
    # 关键断言:原 key 字符串不能在文件里出现
    assert secret not in text
    # 应当有某种加密/编码前缀(fernet: 或 b64:)
    import json
    data = json.loads(text)
    assert "api_key_enc" in data
    assert data["api_key_enc"].startswith(("fernet:", "b64:"))


# ---------------------------------------------------------------------------
# 10. 跨 user 隔离
# ---------------------------------------------------------------------------


def test_state_isolated_between_users(client):
    # user_a 完成
    client.post(
        "/api/onboarding/complete",
        params={"user_id": "user_a"},
        json={"llm_provider": "disabled"},
    )
    # user_b 没完成
    resp = client.get("/api/onboarding/state", params={"user_id": "user_b"})
    assert resp.json()["completed"] is False

    # user_a 应该是 completed
    resp_a = client.get("/api/onboarding/state", params={"user_id": "user_a"})
    assert resp_a.json()["completed"] is True


# ---------------------------------------------------------------------------
# 11. user_id 校验
# ---------------------------------------------------------------------------


def test_user_id_empty_rejected(client):
    resp = client.get("/api/onboarding/state", params={"user_id": ""})
    assert resp.status_code == 400


def test_user_id_path_traversal_rejected(client):
    resp = client.get("/api/onboarding/state", params={"user_id": "../etc"})
    assert resp.status_code == 400


def test_user_id_special_chars_rejected(client):
    resp = client.get("/api/onboarding/state", params={"user_id": "alice/bob"})
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# 12. vendor_status 字段稳定
# ---------------------------------------------------------------------------


def test_state_vendor_status_shape_is_stable(client):
    resp = client.get("/api/onboarding/state", params={"user_id": "stable"})
    body = resp.json()
    vs = body["vendor_status"]
    assert "proto_language" in vs
    assert "ml_models" in vs
    assert "local_llm" in vs
    for k in ("available", "size_mb", "path"):
        assert k in vs["proto_language"]
    for k in ("available", "size_mb", "path", "model_name"):
        assert k in vs["local_llm"]


# ---------------------------------------------------------------------------
# 13. (附加) 路径未知 llm_provider → 422
# ---------------------------------------------------------------------------


def test_complete_unknown_llm_provider_rejected(client):
    resp = client.post(
        "/api/onboarding/complete",
        params={"user_id": "frank"},
        json={"llm_provider": "future-quantum"},
    )
    # Pydantic 422(枚举校验)
    assert resp.status_code == 422
