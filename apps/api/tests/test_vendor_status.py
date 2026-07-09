"""Phase 3 Task 1.5 — vendor status 端点测试。

覆盖点(>= 6 测试):
1. `GET /api/vendor/status` 返回 200 + 三个 vendor 的 available 字段
2. proto-language 在真实环境(已就位) → available=True
3. ESM2-150M 在真实环境(已就位) → available=True
4. local_llm 在真实环境(已就位) → available=True
5. spliceai 在真实环境(只有 README) → available=False
6. splice-transformer 在真实环境(只有 README) → available=False
7. 隔离 vendor root 场景:所有 available=False 时 endpoint 仍能返回合法结构
8. 响应字段稳定性:字段名必须与前端 `VendorStatus` 类型一致
"""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import llm
from app.config import settings
from app.llm import loader as llm_loader_mod
from app.llm.loader import LocalLLMLoader
from app.main import app
from app.models.loader import (
    reset_vendor_root,
)


# ---------------------------------------------------------------------------
# 通用 fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _isolated_data_dir(tmp_path, monkeypatch):
    """与其他 api 测试一致:把 llm.json 写到 tmp,避免污染真实数据目录。"""
    test_dir = tmp_path / "data"
    test_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(settings, "data_dir", test_dir)
    monkeypatch.setattr(llm, "_CONFIG_PATH", test_dir / "llm.json")
    yield


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(autouse=True)
def _isolate_vendor_root_for_models():
    """models/loader 的 vendor_root 在 case 之间需要重置,避免污染。"""
    reset_vendor_root()
    yield
    reset_vendor_root()


@pytest.fixture(autouse=True)
def _isolate_llm_vendor_dir(monkeypatch, tmp_path):
    """local LLM 的 vendor_dir 是模块级常量,monkeypatch 到 tmp_path。

    本测试中 LLM 资源是真实就位(4.6GB),不需要隔离重写;
    但为了"隔离 vendor root 场景"那一个 case 能切到空目录,
    我们用 monkeypatch 默认指向 tmp,但在 case 里会再切回真实路径。
    """
    fake = tmp_path / "vendor_llm_iso"
    monkeypatch.setattr(llm_loader_mod, "_DEFAULT_VENDOR_LLM", fake)
    yield


def _restore_real_llm_vendor_dir():
    """让 LocalLLMLoader.vendor_dir 指向真实 apps/api/vendor/llm(测试已就位资源用)。"""
    real_path = llm_loader_mod._API_ROOT / "vendor" / "llm"
    LocalLLMLoader.__dict__  # touch to ensure class loaded
    # 直接替换模块级常量,使 LocalLLMLoader() 默认指向真实路径
    llm_loader_mod._DEFAULT_VENDOR_LLM = real_path


# ---------------------------------------------------------------------------
# 1. 基本返回结构
# ---------------------------------------------------------------------------


def test_status_returns_200_and_three_sections(client):
    resp = client.get("/api/vendor/status")
    assert resp.status_code == 200
    body = resp.json()
    assert "proto_language" in body
    assert "ml_models" in body
    assert "local_llm" in body


def test_status_response_shape_is_stable(client):
    """字段名必须与前端 VendorStatus 类型一致,不能随便改。"""
    resp = client.get("/api/vendor/status")
    body = resp.json()

    # proto_language 必有:available / size_mb / path
    for key in ("available", "size_mb", "path"):
        assert key in body["proto_language"], f"proto_language missing {key}"

    # ml_models 三个子项,且每个子项都应有 available / size_mb / path
    assert set(body["ml_models"].keys()) == {"esm2-150m", "spliceai", "splice-transformer"}
    for name, info in body["ml_models"].items():
        for key in ("available", "size_mb", "path"):
            assert key in info, f"ml_models[{name}] missing {key}"

    # local_llm 必有:available / size_mb / path / model_name
    for key in ("available", "size_mb", "path", "model_name"):
        assert key in body["local_llm"], f"local_llm missing {key}"
    assert body["local_llm"]["model_name"] == "Qwen2.5-7B-Instruct-Q4_K_M"


# ---------------------------------------------------------------------------
# 2. 真实 vendor 环境下的 available 判定
# ---------------------------------------------------------------------------


def test_proto_language_available_in_real_vendor(client):
    """proto-language 已经在 Task 1.1 阶段 vendored 到 apps/api/vendor/proto-language/,
    build/lib/proto_language/__init__.py 必须存在。"""
    resp = client.get("/api/vendor/status")
    body = resp.json()
    assert body["proto_language"]["available"] is True
    assert body["proto_language"]["size_mb"] > 0
    assert body["proto_language"]["path"] == "vendor/proto-language/build/lib"


def test_esm2_150m_available_in_real_vendor(client):
    """ESM2-150M 已经在 Task 1.2 阶段下载到 apps/api/vendor/models/esm2-150m/model.safetensors(595MB)。"""
    resp = client.get("/api/vendor/status")
    body = resp.json()
    assert body["ml_models"]["esm2-150m"]["available"] is True
    assert body["ml_models"]["esm2-150m"]["size_mb"] >= 500
    assert "esm2-150m" in body["ml_models"]["esm2-150m"]["path"]


def test_local_llm_available_in_real_vendor(client):
    """Qwen2.5-7B 已经在 Task 1.3 阶段 vendored(4.6GB,分片 2 个)。

    我们用 `client.app` 重新构造一个 LLMStatusQuery 时,先把 _DEFAULT_VENDOR_LLM
    指回真实路径,再发起请求。
    """
    _restore_real_llm_vendor_dir()
    # 重新 import 让模块拿到新的 _DEFAULT_VENDOR_LLM
    import importlib
    importlib.reload(llm_loader_mod)

    # FastAPI app 已经 import 过 LLM provider 实例,但 vendor_router
    # 是每次请求重新调 `_local_llm_status()`,所以 reload 之后能拿到真实路径
    from app.routers import vendor as vendor_router_mod
    importlib.reload(vendor_router_mod)
    # 重新把 reload 后的 router include 到 app
    app.include_router(vendor_router_mod.router, prefix="/api/vendor", tags=["vendor-reload"])

    resp = client.get("/api/vendor/status")
    body = resp.json()
    assert body["local_llm"]["available"] is True
    assert body["local_llm"]["size_mb"] >= 3500
    assert "llm" in body["local_llm"]["path"]
    assert body["local_llm"]["model_name"] == "Qwen2.5-7B-Instruct-Q4_K_M"


# ---------------------------------------------------------------------------
# 3. README-only 场景 → available=False
# ---------------------------------------------------------------------------


def test_spliceai_unavailable_in_real_vendor(client):
    """spliceai 目录只有 README.md(Task 1.2 阶段没下载权重)。"""
    resp = client.get("/api/vendor/status")
    body = resp.json()
    assert body["ml_models"]["spliceai"]["available"] is False
    assert body["ml_models"]["spliceai"]["size_mb"] == 0
    assert "spliceai" in body["ml_models"]["spliceai"]["path"]


def test_splice_transformer_unavailable_in_real_vendor(client):
    """splice-transformer 目录只有 README.md。"""
    resp = client.get("/api/vendor/status")
    body = resp.json()
    assert body["ml_models"]["splice-transformer"]["available"] is False
    assert body["ml_models"]["splice-transformer"]["size_mb"] == 0
    assert "splice-transformer" in body["ml_models"]["splice-transformer"]["path"]


# ---------------------------------------------------------------------------
# 4. 隔离 vendor root 场景:所有 available=False 时 endpoint 仍能返回合法结构
# ---------------------------------------------------------------------------


def test_status_all_unavailable_when_vendor_is_empty(client, tmp_path, monkeypatch):
    """把 models/loader 切到一个空 vendor root,所有 ML 模型应 unavailable;
    local_llm 因为 _isolate_llm_vendor_dir 指向空 tmp → unavailable。

    这条测试确保 vendor status 在"全新 ML 资源环境"下能正常返回结构,
    而不是抛 500。proto-language 走的是硬编码绝对路径,这条测试不验证它。
    """
    from app.models.loader import override_vendor_root
    override_vendor_root(tmp_path / "empty_vendor")

    resp = client.get("/api/vendor/status")
    assert resp.status_code == 200
    body = resp.json()
    for name in ("esm2-150m", "spliceai", "splice-transformer"):
        assert body["ml_models"][name]["available"] is False
        assert body["ml_models"][name]["size_mb"] == 0
    assert body["local_llm"]["available"] is False
    assert body["local_llm"]["size_mb"] == 0
    # model_name 字段始终存在(就算不可用)
    assert body["local_llm"]["model_name"] == "Qwen2.5-7B-Instruct-Q4_K_M"


def test_status_proto_language_unavailable_when_build_lib_missing(
    client, tmp_path, monkeypatch
):
    """proto-language 的判定走硬编码绝对路径,直接 monkeypatch 那个常量来测 unavailable 分支。"""
    from app.routers import vendor as vendor_router_mod
    fake = tmp_path / "no_proto_language"
    monkeypatch.setattr(vendor_router_mod, "_PROTO_LANGUAGE_BUILD_LIB", fake)

    resp = client.get("/api/vendor/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["proto_language"]["available"] is False
    assert body["proto_language"]["size_mb"] == 0
