"""Translate 路由。"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.llm import load_state
from app.missions import get_mission
from app.schemas import TranslateRequest, TranslateResponse
from app.translate import translate

router = APIRouter(prefix="/api/translate", tags=["translate"])


@router.post("", response_model=TranslateResponse)
def translate_text(req: TranslateRequest) -> TranslateResponse:
    try:
        mission = get_mission(req.mission_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Unknown mission: {req.mission_id}") from exc

    values, explanation = translate(req.text, mission)
    state = load_state()
    return TranslateResponse(
        mission_id=req.mission_id,
        values=values,
        explanation=explanation,
        provider=state.active,
    )
