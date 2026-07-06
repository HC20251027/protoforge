"""Gallery 路由(Phase 1:内存;Task 13 切 SQLite)。"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.gallery_store import add, get, list_all
from app.schemas import Artifact, ArtifactCreate, ArtifactListResponse

router = APIRouter(prefix="/api/gallery", tags=["gallery"])


@router.get("", response_model=ArtifactListResponse)
def list_items() -> ArtifactListResponse:
    return list_all()


@router.post("", response_model=Artifact)
def create(req: ArtifactCreate) -> Artifact:
    return add(req)


@router.get("/{artifact_id}", response_model=Artifact)
def detail(artifact_id: str) -> Artifact:
    item = get(artifact_id)
    if item is None:
        raise HTTPException(status_code=404, detail="artifact not found")
    return item
