"""Phase 3 Task 6 P0-A1: gallery_store 不再用 asyncio.run 阻塞 event loop。

修复前:sync handler 调 `asyncio.run(_coro)`,在 FastAPI thread pool
里会因 "asyncio.run() cannot be called from a running event loop" 抛
RuntimeError,或更糟:阻塞主 event loop 几秒,期间其他请求全部卡住。

修复后:用 `anyio.from_thread.run` 在独立后台 event loop 上跑异步
SQLAlchemy 调用,主 event loop 不再被阻塞。

测试策略:跑 FastAPI app(用 TestClient),并发发出 2 个 list 请求。
如果 event loop 被阻塞,总耗时接近 2 倍单请求耗时;如果不被阻塞,
总耗时接近单请求耗时。
"""
import time
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from app import gallery_store
from app.config import settings
from app.main import app


@pytest.fixture(autouse=True)
def _memory_backend(tmp_path, monkeypatch):
    """强制 memory backend,避免并发请求共享 SQLite 连接时互相干扰。"""
    test_dir = tmp_path / "data"
    test_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(settings, "data_dir", test_dir)
    monkeypatch.setattr(settings, "db_path", test_dir / "test.db")
    gallery_store.set_backend("memory")
    gallery_store.reset()
    yield
    gallery_store.reset()


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def test_gallery_store_uses_nonblocking_runner(client):
    """gallery_store 调 add/list/get/reset 时,不能因 asyncio.run 卡死。

    验证手段:跑 100 次 list,检查单次调用耗时 < 100ms(同步函数 + 内存后端)。
    如果旧 asyncio.run 路径有 side effect(比如后台线程开了未关闭的 loop),
    也会在这里被 timeout 抓到。
    """
    t0 = time.perf_counter()
    for _ in range(100):
        result = gallery_store.list_all()
        assert result.total >= 0
    elapsed = time.perf_counter() - t0
    assert elapsed < 1.0, f"100 次 list 耗时 {elapsed:.2f}s,太慢(可能 event loop 被卡)"


def test_concurrent_list_requests_dont_block_each_other(client):
    """并发发出 N 个 list 请求 — 总耗时应接近单请求耗时,不是 N 倍。

    这才是"event loop 没被阻塞"的关键证据。
    """
    # 先添加一些数据,避免空 list 太快
    from app.schemas import ArtifactCreate

    for i in range(5):
        gallery_store.add(
            ArtifactCreate(
                mission_id="polar-glow-v1",
                title=f"item-{i}",
                intron="GT" + "ATGC" * 10 + "AG",
                fasta=f">x\nGTATGCAG\n",
                scores={"primary": 0.5, "components": {}, "weights": {}},
                ritual="urgent",
                notes=None,
                risk_passed=True,
            )
        )

    n = 8

    def do_list():
        r = client.get("/api/gallery")
        assert r.status_code == 200
        return r.json()["total"]

    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=n) as pool:
        totals = list(pool.map(lambda _: do_list(), range(n)))
    elapsed = time.perf_counter() - t0

    # 全部应返回 5(我们刚 add 的 5 个)
    assert totals == [5] * n
    # 并发 8 个 list,总耗时不应超过 1 秒(单次 list 在内存后端 < 10ms)
    # 旧 asyncio.run 路径会因 event loop 冲突报 RuntimeError,这里就 fail
    assert elapsed < 1.0, f"并发 8 个 list 耗时 {elapsed:.2f}s,event loop 可能被阻塞"


def test_concurrent_add_and_list_interleaved(client):
    """并发 add + list 混合 — 验证读写都不阻塞。"""
    from app.schemas import ArtifactCreate

    def do_add(i):
        gallery_store.add(
            ArtifactCreate(
                mission_id="polar-glow-v1",
                title=f"add-{i}",
                intron="GT" + "ATGC" * 5 + "AG",
                fasta=f">x\nGTATGCAG\n",
                scores={"primary": 0.5, "components": {}, "weights": {}},
                ritual="urgent",
                notes=None,
                risk_passed=True,
            )
        )

    def do_list():
        r = client.get("/api/gallery")
        return r.status_code, r.json()["total"]

    n = 4
    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=n * 2) as pool:
        list_futs = [pool.submit(do_list) for _ in range(n)]
        add_futs = [pool.submit(do_add, i) for i in range(n)]
        list_results = [f.result() for f in list_futs]
        for f in add_futs:
            f.result()
    elapsed = time.perf_counter() - t0

    # 全部 list 成功
    assert all(s == 200 for s, _ in list_results)
    # add 都跑完 → 最后 list 应有 4 个
    final = gallery_store.list_all()
    assert final.total == 4
    # 总耗时 < 1s
    assert elapsed < 1.0, f"add+list 混合并发耗时 {elapsed:.2f}s,可能 event loop 被阻塞"
