"""Risk Gate:玩家在 forge 后必须答对生物安全 + 跨物种伦理题。"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.missions import get_mission
from app.schemas import RiskCheckItem, RiskCheckRequest, RiskCheckResponse

router = APIRouter(prefix="/api/risk", tags=["risk"])


@router.post("/check", response_model=RiskCheckResponse)
def check(req: RiskCheckRequest) -> RiskCheckResponse:
    try:
        mission = get_mission(req.mission_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Unknown mission: {req.mission_id}") from exc

    items: list[RiskCheckItem] = []
    correct_count = 0
    blocked = False

    for rule in mission.risk_rules:
        user = req.answers.get(rule.rule_id, "")
        is_correct = user == rule.correct
        if is_correct:
            correct_count += 1
        if rule.severity == "block" and not is_correct:
            blocked = True
        items.append(
            RiskCheckItem(
                rule_id=rule.rule_id,
                user_answer=user,
                correct=is_correct,
                explanation=rule.explanation,
                severity=rule.severity,
            )
        )

    total = max(1, len(mission.risk_rules))
    score = round(correct_count / total, 3)
    passed = (not blocked) and (correct_count == total)

    return RiskCheckResponse(
        mission_id=req.mission_id,
        passed=passed,
        items=items,
        score=score,
    )
