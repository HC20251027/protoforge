"""任务列表 + 详情。"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.missions import get_mission, list_missions
from app.schemas import Mission

router = APIRouter(prefix="/api/missions", tags=["missions"])


@router.get("", response_model=list[Mission])
def list_all() -> list[Mission]:
    return list_missions()


@router.get("/{mission_id}", response_model=Mission)
def detail(mission_id: str) -> Mission:
    try:
        return get_mission(mission_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Unknown mission: {mission_id}") from exc
