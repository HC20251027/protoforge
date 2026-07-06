"""Gallery 内存 store(Phase 1),Task 13 替换为 SQLite。"""
from __future__ import annotations

import threading
import time
import uuid
from typing import Iterable

from app.schemas import Artifact, ArtifactCreate, ArtifactListResponse

_lock = threading.RLock()
_items: dict[str, Artifact] = {}


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()) + f".{int(time.time() * 1000) % 1000:03d}"


def add(req: ArtifactCreate) -> Artifact:
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
    with _lock:
        _items[artifact.id] = artifact
    return artifact


def list_all() -> ArtifactListResponse:
    with _lock:
        items = sorted(
            _items.values(),
            key=lambda a: a.created_at,
            reverse=True,
        )
    return ArtifactListResponse(items=items, total=len(items))


def get(artifact_id: str) -> Artifact | None:
    with _lock:
        return _items.get(artifact_id)


def reset() -> None:
    """测试/开发态清空。"""
    with _lock:
        _items.clear()
