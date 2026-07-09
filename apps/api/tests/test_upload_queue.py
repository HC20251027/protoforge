"""Phase 3 Task 5: UploadQueue 测试。"""
import json
from pathlib import Path

import pytest

from app.protoforge.queue import (
    STATUS_CANCELLED,
    STATUS_FAILED,
    STATUS_PENDING,
    STATUS_UPLOADED,
    UploadQueue,
    queue_for,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def queue_root(tmp_path: Path) -> Path:
    return tmp_path / "upload_queue"


@pytest.fixture()
def queue(queue_root: Path) -> UploadQueue:
    return UploadQueue.for_player("alice", queue_root=queue_root)


@pytest.fixture()
def fake_export(tmp_path: Path) -> Path:
    p = tmp_path / "fake.protoforge"
    p.write_bytes(b"fake zip content for test")
    return p


# ---------------------------------------------------------------------------
# 测试 1:enqueue + peek + list_pending
# ---------------------------------------------------------------------------


def test_enqueue_creates_pending_item(queue: UploadQueue, fake_export: Path):
    """enqueue 之后,list_pending 必须能看到该项,status=pending。"""
    qid = queue.enqueue(
        export_path=fake_export,
        mission_id="polar-glow-v1",
        ritual="urgent",
    )
    assert qid.startswith("qu_")
    items = queue.list_pending()
    assert len(items) == 1
    assert items[0].queue_id == qid
    assert items[0].status == STATUS_PENDING
    assert items[0].mission_id == "polar-glow-v1"
    assert items[0].ritual == "urgent"
    assert items[0].attempts == 0


# ---------------------------------------------------------------------------
# 测试 2:mark_uploaded 后从 pending 移到 uploaded
# ---------------------------------------------------------------------------


def test_mark_uploaded_removes_from_pending(queue: UploadQueue, fake_export: Path):
    """mark_uploaded 之后,该 queue_id 不再出现在 list_pending。"""
    qid = queue.enqueue(
        export_path=fake_export,
        mission_id="polar-glow-v1",
        ritual="urgent",
    )
    queue.mark_uploaded(qid, workshop_id="mock_abc123")

    # pending 列表里没有
    pending = queue.list_pending()
    assert all(it.queue_id != qid for it in pending)
    # 但 list_all 仍能看到
    all_items = queue.list_all()
    assert len(all_items) == 1
    assert all_items[0].status == STATUS_UPLOADED
    assert all_items[0].workshop_id == "mock_abc123"
    assert all_items[0].error is None
    # attempts 计数 +1
    assert all_items[0].attempts == 1


# ---------------------------------------------------------------------------
# 测试 3:mark_failed 保留 item 用于重试
# ---------------------------------------------------------------------------


def test_mark_failed_keeps_item_for_retry(queue: UploadQueue, fake_export: Path):
    """mark_failed 之后,该 item **仍** 出现在 list_pending(可重试)。"""
    qid = queue.enqueue(
        export_path=fake_export,
        mission_id="polar-glow-v1",
        ritual="urgent",
    )
    queue.mark_failed(qid, error="network timeout")

    # 仍出现在 pending 列表(可重试)
    pending = queue.list_pending()
    assert len(pending) == 1
    assert pending[0].queue_id == qid
    assert pending[0].status == STATUS_FAILED
    assert pending[0].error == "network timeout"
    assert pending[0].attempts == 1


# ---------------------------------------------------------------------------
# 测试 4:跨进程持久化(JSON 文件)
# ---------------------------------------------------------------------------


def test_persistence_across_processes(queue_root: Path, fake_export: Path):
    """新进程(新 UploadQueue 实例)必须能读到上次 enqueue 的数据。"""
    # 进程 1:入队
    q1 = UploadQueue.for_player("bob", queue_root=queue_root)
    q1.enqueue(
        export_path=fake_export,
        mission_id="polar-glow-v1",
        ritual="ancient",
    )
    q1.enqueue(
        export_path=fake_export,
        mission_id="polar-glow-v1",
        ritual="crystal",
    )

    # 进程 2:重新构造,必须能读到 2 条
    q2 = UploadQueue.for_player("bob", queue_root=queue_root)
    items = q2.list_pending()
    assert len(items) == 2
    missions = {it.mission_id for it in items}
    rituals = {it.ritual for it in items}
    assert missions == {"polar-glow-v1"}
    assert rituals == {"ancient", "crystal"}

    # 进程 2:标 uploaded
    qids = [it.queue_id for it in items]
    q2.mark_uploaded(qids[0], workshop_id="mock_xyz")

    # 进程 3:重新构造,确认状态已持久化
    q3 = UploadQueue.for_player("bob", queue_root=queue_root)
    all_items = q3.list_all()
    assert len(all_items) == 2
    statuses = {it.queue_id: it.status for it in all_items}
    assert statuses[qids[0]] == STATUS_UPLOADED
    assert statuses[qids[1]] == STATUS_PENDING


# ---------------------------------------------------------------------------
# 测试 5:peek / pending_count / cancel / get
# ---------------------------------------------------------------------------


def test_peek_count_cancel_get(queue: UploadQueue, fake_export: Path):
    """综合测试:peek / pending_count / cancel / get。"""
    # 空队列
    assert queue.pending_count() == 0
    assert queue.peek() == []

    # 入 3 条
    qid1 = queue.enqueue(fake_export, "polar-glow-v1", "urgent")
    qid2 = queue.enqueue(fake_export, "polar-glow-v1", "standard")
    qid3 = queue.enqueue(fake_export, "polar-glow-v1", "ancient")
    assert queue.pending_count() == 3
    assert len(queue.peek()) == 3

    # get
    it = queue.get(qid2)
    assert it is not None
    assert it.queue_id == qid2
    assert queue.get("nonexistent") is None

    # cancel
    queue.cancel(qid3)
    assert queue.pending_count() == 2  # cancelled 不算 pending
    cancelled = queue.get(qid3)
    assert cancelled.status == STATUS_CANCELLED


# ---------------------------------------------------------------------------
# 测试 6:player_id 非法 → ValueError
# ---------------------------------------------------------------------------


def test_queue_rejects_invalid_player_id(queue_root: Path):
    """防路径穿越:player_id 含非法字符应抛 ValueError。"""
    with pytest.raises(ValueError, match="player_id 非法"):
        UploadQueue.for_player("../etc", queue_root=queue_root)
    with pytest.raises(ValueError, match="player_id 非法"):
        UploadQueue.for_player("alice/bob", queue_root=queue_root)


# ---------------------------------------------------------------------------
# 测试 7:enqueue 文件不存在 → FileNotFoundError
# ---------------------------------------------------------------------------


def test_enqueue_missing_file_raises(queue: UploadQueue):
    """enqueue 传入不存在的文件应抛 FileNotFoundError。"""
    with pytest.raises(FileNotFoundError):
        queue.enqueue(
            export_path=Path("/tmp/does_not_exist.protoforge"),
            mission_id="polar-glow-v1",
            ritual="urgent",
        )
