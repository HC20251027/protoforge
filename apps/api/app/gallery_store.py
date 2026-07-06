"""Gallery store(Phase 1.5: SQLite 持久化)。

- `backend = "sqlite"`:默认,写到 settings.db_path。
- `backend = "memory"`:仅用于测试,通过 set_backend() 切换。
- 旧 API(add/list_all/get/reset)保持同步形态;底层走 SQLite 时每个函数实际是
  一次性 await(在 sync router 里由 gallery router 包装成 async handler)。
"""
from __future__ import annotations

import time
import uuid
from typing import Any

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

import threading

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
# ---------------------------------------------------------------------------

def add(req: ArtifactCreate) -> Artifact:
    if _BACKEND == "memory":
        return _add_mem(req)
    # 同步入口 — 跑 event loop 一次。pytest 用 TestClient 已经在线程里,
    # 用 asyncio.run 是安全的(每个请求一个新 loop)。
    import asyncio
    return asyncio.run(_add_sqlite(req))


def list_all() -> ArtifactListResponse:
    if _BACKEND == "memory":
        return _list_mem()
    import asyncio
    return asyncio.run(_list_sqlite())


def get(artifact_id: str) -> Artifact | None:
    if _BACKEND == "memory":
        return _get_mem(artifact_id)
    import asyncio
    return asyncio.run(_get_sqlite(artifact_id))


def reset() -> None:
    """测试/开发态清空。memory backend 直接清;sqlite backend 删表重建。"""
    if _BACKEND == "memory":
        _reset_mem()
        return
    import asyncio
    from app.db import Base, get_engine

    async def _do():
        engine = get_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(_do())
