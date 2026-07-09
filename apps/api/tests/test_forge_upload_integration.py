"""Phase 3 Task 5: Forge 上传集成测试。

测试 `POST /api/forge/run` 通关后自动触发 Steam 上传流程。
"""
import os
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app import gallery_store
from app.config import settings
from app.main import app
from app.protoforge import queue as queue_mod
from app.protoforge import steam as steam_mod
from app.protoforge.queue import UploadQueue
from app.protoforge.steam import SteamWorkshopUploader


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _isolated_data(monkeypatch, tmp_path):
    """每个测试用独立 tmp 目录(避免污染默认路径)。"""
    test_dir = tmp_path / "data"
    test_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(settings, "data_dir", test_dir)
    monkeypatch.setattr(settings, "db_path", test_dir / "test.db")
    # 强制 packager/queue 用测试目录
    test_exports = test_dir / "exports"
    test_queue = test_dir / "upload_queue"
    test_exports.mkdir(parents=True, exist_ok=True)
    test_queue.mkdir(parents=True, exist_ok=True)
    gallery_store.set_backend("memory")
    gallery_store.reset()
    # 默认 player_id 隔离
    monkeypatch.setenv("PROTOFORGE_PLAYER_ID", "default")
    yield
    gallery_store.reset()


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


# ---------------------------------------------------------------------------
# 工具:构造一个通过的 forge run
# ---------------------------------------------------------------------------


def _passing_forge_body():
    """构造能让 risk_gate_passed=True + score >= 0.5 的 forge body。

    用 min_target_splice 极低 + max_off_target 极高 → 强制 passes_thresholds。
    """
    return {
        "mission_id": "polar-glow-v1",
        "params": {
            "min_target_splice": 0.0,  # 极低 → 必过
            "max_off_target": 1.0,     # 极高 → 必过
        },
        "generator": "preference",
        "seed": 42,
        "ritual": "urgent",
    }


def _failing_forge_body():
    """构造让 risk_gate_passed=False 的 forge body。

    用 min_target_splice 极高 → 必不过。
    """
    return {
        "mission_id": "polar-glow-v1",
        "params": {
            "min_target_splice": 1.5,  # 超出 [0,1] 范围 → 评分会很低
        },
        "generator": "preference",
        "seed": 42,
        "ritual": "urgent",
    }


# ---------------------------------------------------------------------------
# 测试 1:通关后返回 upload.queued=true + workshop_id (mock 模式下 Steam "在运行")
# ---------------------------------------------------------------------------


def test_forge_run_passing_queues_and_uploads_with_steam_running(client: TestClient):
    """通关 + Steam "在运行" → upload.queued=true + workshop_id + status=uploaded。"""
    # mock:is_steam_running 返回 True,upload_item 返回 mock_xxx
    with patch.object(SteamWorkshopUploader, "is_steam_running", return_value=True), \
         patch.object(SteamWorkshopUploader, "upload_item", return_value="mock_deadbeef12345678") as m_upload:
        # 重置单例,让 mock 生效
        steam_mod.reset_default_uploader()
        try:
            resp = client.post("/api/forge/run", json=_passing_forge_body())
            assert resp.status_code == 200, resp.text
            data = resp.json()

            # upload 字段必须存在
            assert "upload" in data
            upload = data["upload"]
            assert upload["queued"] is True
            assert upload["workshop_id"] == "mock_deadbeef12345678"
            assert upload["status"] == "uploaded"
            assert upload["queue_id"] is not None
            assert "已上传" in upload["message"]

            # upload_item 真的被调用了
            assert m_upload.called
        finally:
            steam_mod.reset_default_uploader()


# ---------------------------------------------------------------------------
# 测试 2:不通关(评分 < 阈值) → upload.queued=false
# ---------------------------------------------------------------------------


def test_forge_run_failing_does_not_queue(client: TestClient):
    """不通关(评分 < 阈值 / risk_gate 未过)→ upload.queued=false, status=skipped。"""
    resp = client.post("/api/forge/run", json=_failing_forge_body())
    assert resp.status_code == 200, resp.text
    data = resp.json()
    upload = data["upload"]
    assert upload["queued"] is False
    assert upload["workshop_id"] is None
    assert upload["queue_id"] is None
    assert upload["status"] == "skipped"
    # passed_gate 必须是 False
    assert data["passed_gate"] is False


# ---------------------------------------------------------------------------
# 测试 3:通关 + Steam 未运行 → 留队, status=queued
# ---------------------------------------------------------------------------


def test_forge_run_passing_steam_not_running_stays_queued(client: TestClient):
    """通关 + Steam 没运行 → 留队, status=queued, workshop_id=None。"""
    # mock:is_steam_running 返回 False
    with patch.object(SteamWorkshopUploader, "is_steam_running", return_value=False):
        steam_mod.reset_default_uploader()
        try:
            resp = client.post("/api/forge/run", json=_passing_forge_body())
            assert resp.status_code == 200, resp.text
            data = resp.json()
            upload = data["upload"]
            assert upload["queued"] is True
            assert upload["workshop_id"] is None  # 没传上去
            assert upload["status"] == "queued"
            assert upload["queue_id"] is not None
        finally:
            steam_mod.reset_default_uploader()


# ---------------------------------------------------------------------------
# 测试 4:GET /api/protoforge/queue 返回刚入队的作品
# ---------------------------------------------------------------------------


def test_queue_endpoint_returns_enqueued_item(client: TestClient):
    """GET /api/protoforge/queue?player_id=xxx 应返回刚入队的作品。"""
    # 1) 通关入队
    with patch.object(SteamWorkshopUploader, "is_steam_running", return_value=False):
        steam_mod.reset_default_uploader()
        try:
            resp = client.post("/api/forge/run", json=_passing_forge_body())
            assert resp.status_code == 200
            assert resp.json()["upload"]["queued"] is True
        finally:
            steam_mod.reset_default_uploader()

    # 2) 列队列
    resp = client.get("/api/protoforge/queue", params={"player_id": "default"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["pending_count"] == 1
    assert len(data["items"]) == 1
    it = data["items"][0]
    assert it["mission_id"] == "polar-glow-v1"
    assert it["ritual"] == "urgent"
    assert it["status"] in ("pending", "failed", "queued")


# ---------------------------------------------------------------------------
# 测试 5:POST /api/protoforge/queue/retry 重试
# ---------------------------------------------------------------------------


def test_queue_retry_endpoint_uploads_pending(client: TestClient):
    """入队后再 retry,应能上传成功。"""
    # 1) 通关 + Steam 未运行 → 留队
    with patch.object(SteamWorkshopUploader, "is_steam_running", return_value=False):
        steam_mod.reset_default_uploader()
        try:
            client.post("/api/forge/run", json=_passing_forge_body())
        finally:
            steam_mod.reset_default_uploader()

    # 2) Steam 启动,retry 应该能上传
    with patch.object(SteamWorkshopUploader, "is_steam_running", return_value=True), \
         patch.object(SteamWorkshopUploader, "upload_item", return_value="mock_retry_aaa") as m_upload:
        steam_mod.reset_default_uploader()
        try:
            resp = client.post(
                "/api/protoforge/queue/retry",
                params={"player_id": "default"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["attempted"] == 1
            assert data["uploaded"] == 1
            assert data["failed"] == 0
            assert m_upload.called
        finally:
            steam_mod.reset_default_uploader()

    # 3) 再列队列,应该已经 uploaded
    resp = client.get("/api/protoforge/queue", params={"player_id": "default"})
    pending = resp.json()["pending_count"]
    assert pending == 0  # uploaded 不算 pending


# ---------------------------------------------------------------------------
# 测试 6:GET /api/protoforge/exports 返回已打包文件
# ---------------------------------------------------------------------------


def test_exports_endpoint_returns_packed_files(client: TestClient):
    """通关后,GET /api/protoforge/exports?player_id=xxx 应返回 .protoforge 文件。"""
    # 1) 通关
    with patch.object(SteamWorkshopUploader, "is_steam_running", return_value=False):
        steam_mod.reset_default_uploader()
        try:
            client.post("/api/forge/run", json=_passing_forge_body())
        finally:
            steam_mod.reset_default_uploader()

    # 2) 列导出
    resp = client.get("/api/protoforge/exports", params={"player_id": "default"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    it = data["items"][0]
    assert it["filename"].endswith(".protoforge")
    assert it["size_bytes"] > 0
    assert it["manifest"]["mission_id"] == "polar-glow-v1"
