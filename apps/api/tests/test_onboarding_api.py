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


# ---------------------------------------------------------------------------
# Phase 4 Task A1: cryptography / Fernet 加密层测试
# ---------------------------------------------------------------------------
#
# 这些测试只验证 _encrypt_secret / _decrypt_secret / _ensure_key 的契约。
# 不改 onboarding.py 现有代码,只 import 其内部函数。
#

from app.routers import onboarding as onboarding_router  # noqa: E402


def test_fernet_encrypt_decrypt():
    """明文 → encrypt → decrypt → 等于明文(Fernet 路径)。"""
    # 显式传 fernet key,确保走 fernet 分支
    from cryptography.fernet import Fernet

    key = Fernet.generate_key()
    plain = "sk-test-plaintext-1234567890"

    enc = onboarding_router._encrypt_secret(plain)  # type: ignore[attr-defined]
    # 显式走文件路径会读到 on-disk key;这里只断言 encrypt + decrypt 自洽:
    # 用同一个 key 重新实例化 _decrypt_secret 必须能解出明文
    # 但 _decrypt_secret 会自己调 _ensure_key(),需要先让 key 文件就位
    # → 简化:用 on-disk fernet key 路径(已自动生成),验证 encrypt/decrypt 自洽
    assert enc.startswith("fernet:") or enc.startswith("b64:")

    # 强制走"fernet 路径":把 _KEY_PATH 写到临时 fernet key,然后 encrypt+decrypt
    from pathlib import Path

    import app.routers.onboarding as ob

    test_key_file = ob._KEY_PATH  # type: ignore[attr-defined]
    test_key_file.parent.mkdir(parents=True, exist_ok=True)
    test_key_file.write_text(f"FERNET:{key.decode('ascii')}\n", encoding="utf-8")

    enc2 = onboarding_router._encrypt_secret(plain)  # type: ignore[attr-defined]
    assert enc2.startswith("fernet:")
    dec = onboarding_router._decrypt_secret(enc2)  # type: ignore[attr-defined]
    assert dec == plain


def test_fernet_key_from_env(monkeypatch, tmp_path):
    """PROTOFORGE_KEY 环境变量走 fernet 路径。"""
    from cryptography.fernet import Fernet

    # 数据目录隔离
    test_dir = tmp_path / "data_env"
    test_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(settings, "data_dir", test_dir)
    import app.routers.onboarding as ob

    monkeypatch.setattr(ob, "_KEY_PATH", test_dir / ".protoforge_key")
    # 确保 onboarding.py 模块级 _KEY_PATH 也被覆写
    monkeypatch.setattr(onboarding_router, "_KEY_PATH", test_dir / ".protoforge_key")

    key = Fernet.generate_key()
    monkeypatch.setenv("PROTOFORGE_KEY", key.decode("ascii"))

    mode, kb = onboarding_router._ensure_key()  # type: ignore[attr-defined]
    assert mode == "fernet"
    assert kb == key

    plain = "sk-from-env-99999999"
    enc = onboarding_router._encrypt_secret(plain)  # type: ignore[attr-defined]
    assert enc.startswith("fernet:")
    assert onboarding_router._decrypt_secret(enc) == plain  # type: ignore[attr-defined]


def test_fernet_key_persists(tmp_path, monkeypatch):
    """key 文件读写:第二次启动沿用同一把 key。"""
    test_dir = tmp_path / "data_persist"
    test_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(settings, "data_dir", test_dir)
    import app.routers.onboarding as ob

    key_file = test_dir / ".protoforge_key"
    monkeypatch.setattr(ob, "_KEY_PATH", key_file)
    monkeypatch.setattr(onboarding_router, "_KEY_PATH", key_file)
    # 关键:PROTOFORGE_KEY 必须 unset,才会走文件路径
    monkeypatch.delenv("PROTOFORGE_KEY", raising=False)

    # 第一次启动 → 写文件
    mode1, kb1 = onboarding_router._ensure_key()  # type: ignore[attr-defined]
    assert mode1 == "fernet"
    assert key_file.exists()
    on_disk = key_file.read_text(encoding="utf-8").strip()
    assert on_disk.startswith("FERNET:")

    # 第二次启动 → 读同一文件
    mode2, kb2 = onboarding_router._ensure_key()  # type: ignore[attr-defined]
    assert mode2 == "fernet"
    assert kb2 == kb1

    # encrypt 出来的密文,两次启动都能解
    plain = "sk-persistence-test"
    enc = onboarding_router._encrypt_secret(plain)  # type: ignore[attr-defined]
    assert onboarding_router._decrypt_secret(enc) == plain  # type: ignore[attr-defined]
