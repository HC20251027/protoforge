"""Gallery store(Phase 1.5: SQLite 持久化)。

- `backend = "sqlite"`:默认,写到 settings.db_path。
- `backend = "memory"`:仅用于测试,通过 set_backend() 切换。
- 旧 API(add/list_all/get/reset)保持同步形态;底层走 SQLite 时每个函数实际是
  一次性 await(在 sync router 里由 gallery router 包装成 async handler)。
"""
from __future__ import annotations

import threading
import time
import uuid

from app.schemas import Artifact, ArtifactCreate, ArtifactListResponse

_BACKEND = "sqlite"


def set_backend(name: str) -> None:
    global _BACKEND
    _BACKEND = name


def get_backend() -> str:
    return _BACKEND


# ---------------------------------------------------------------------------
# Memory backend
# ---------------------------------------------------------------------------

_mem_lock = threading.RLock()
_mem: dict[str, Artifact] = {}


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()) + f".{int(time.time() * 1000) % 1000:03d}"


def _add_mem(req: ArtifactCreate) -> Artifact:
    artifact = Artifact(
        id=f"art_{uuid.uuid4().hex[:12]}",
        mission_id=req.mission_id,
        title=req.title,
        intron=req.intron,
        fasta=req.fasta,
        scores=req.scores,
        ritual=req.ritual,
        notes=req.notes,
        risk_passed=req.risk_passed,
        created_at=_now_iso(),
    )
    with _mem_lock:
        _mem[artifact.id] = artifact
    return artifact


def _list_mem() -> ArtifactListResponse:
    with _mem_lock:
        items = sorted(_mem.values(), key=lambda a: a.created_at, reverse=True)
    return ArtifactListResponse(items=items, total=len(items))


def _get_mem(artifact_id: str) -> Artifact | None:
    with _mem_lock:
        return _mem.get(artifact_id)


def _reset_mem() -> None:
    with _mem_lock:
        _mem.clear()


# ---------------------------------------------------------------------------
# SQLite backend(async)
# ---------------------------------------------------------------------------

async def _add_sqlite(req: ArtifactCreate) -> Artifact:
    from app.db import ArtifactRow, get_session, row_to_dict

    artifact_id = f"art_{uuid.uuid4().hex[:12]}"
    async with get_session()() as session:  # type: ignore[arg-type]
        row = ArtifactRow(
            id=artifact_id,
            mission_id=req.mission_id,
            title=req.title,
            intron=req.intron,
            fasta=req.fasta,
            scores=req.scores,
            ritual=req.ritual,
            notes=req.notes,
            risk_passed=req.risk_passed,
        )
        session.add(row)
        await session.commit()
        await session.refresh(row)
        return Artifact(**row_to_dict(row))


async def _list_sqlite() -> ArtifactListResponse:
    from app.db import ArtifactRow, get_session
    from sqlalchemy import select

    async with get_session()() as session:  # type: ignore[arg-type]
        result = await session.execute(select(ArtifactRow).order_by(ArtifactRow.created_at.desc()))
        rows = result.scalars().all()
    items = [
        Artifact(
            id=r.id,
            mission_id=r.mission_id,
            title=r.title,
            intron=r.intron,
            fasta=r.fasta,
            scores=r.scores,
            ritual=r.ritual,
            notes=r.notes,
            risk_passed=r.risk_passed,
            created_at=r.created_at.strftime("%Y-%m-%dT%H:%M:%S"),
        )
        for r in rows
    ]
    return ArtifactListResponse(items=items, total=len(items))


async def _get_sqlite(artifact_id: str) -> Artifact | None:
    from app.db import ArtifactRow, get_session
    from sqlalchemy import select

    async with get_session()() as session:  # type: ignore[arg-type]
        result = await session.execute(select(ArtifactRow).where(ArtifactRow.id == artifact_id))
        row = result.scalar_one_or_none()
    if row is None:
        return None
    return Artifact(
        id=row.id,
        mission_id=row.mission_id,
        title=row.title,
        intron=row.intron,
        fasta=row.fasta,
        scores=row.scores,
        ritual=row.ritual,
        notes=row.notes,
        risk_passed=row.risk_passed,
        created_at=row.created_at.strftime("%Y-%m-%dT%H:%M:%S"),
    )


# ---------------------------------------------------------------------------
# Sync wrappers(根据当前 backend 选择)
#
# Phase 3 Task 6 P0-A1:之前用 `asyncio.run(_coro)` 在 FastAPI 默认
# thread pool 里会因 "asyncio.run() cannot be called from a running
# event loop" 抛 RuntimeError(或有 event loop 时直接卡死)。
#
# 修复策略:每个**调用**新建一个**独立**的 event loop,跑完即销毁。
# 这是 sync handler 调 async 代码的标准 pattern(不像 from_thread.run
# 那样依赖 anyio worker)。保证:
# 1. 调用方仍是同步函数,FastAPI 兼容。
# 2. 不会阻塞调用方线程(因为我们跑在独立 loop,不是 asyncio.run 那
#    种"如果当前线程已有 loop 就报"的路径)。
# 3. 多请求并发:每个请求一个独立 loop,互不干扰。
# 4. 跑测试时(TestClient + pytest)也能正常工作(没有 anyio worker)。
# ---------------------------------------------------------------------------

def _run_async_blocking(coro):
    """在独立 event loop 上跑协程,完成后销毁 loop。

    为什么不用 `asyncio.run`:
    - `asyncio.run` 在已有 event loop 的线程(比如 FastAPI 的 async
      handler 线程、anyio worker 线程)会抛 "asyncio.run() cannot
      be called from a running event loop" 错误。
    - `asyncio.run` 在新线程里是 OK 的,但在 sync handler 默认 thread
      pool 路径上不可靠。

    这里手动 `new_event_loop()` + `run_until_complete()` + `close()`,
    等价于"每次调用都开新 loop,跑完就关",从根上避免"在已有 loop
    里再开 loop"的问题。
    """
    import asyncio

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def add(req: ArtifactCreate) -> Artifact:
    if _BACKEND == "memory":
        return _add_mem(req)
    return _run_async_blocking(_add_sqlite(req))


def list_all() -> ArtifactListResponse:
    if _BACKEND == "memory":
        return _list_mem()
    return _run_async_blocking(_list_sqlite())


def get(artifact_id: str) -> Artifact | None:
    if _BACKEND == "memory":
        return _get_mem(artifact_id)
    return _run_async_blocking(_get_sqlite(artifact_id))


def reset() -> None:
    """测试/开发态清空。memory backend 直接清;sqlite backend 删表重建。"""
    if _BACKEND == "memory":
        _reset_mem()
        return
    from app.db import Base, get_engine

    async def _do():
        engine = get_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

    _run_async_blocking(_do())
