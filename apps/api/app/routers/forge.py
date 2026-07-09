"""Forge 路由:生成 + 评分 + 仪式档位(Phase 3 Task 2)。

Phase 3 决策:4 档仪式**不与硬件挂钩**。玩家主动选择难度,系统不自动降级。
`/api/forge/ritual` 返回 4 档的"难度"维度(急锻者徽章 + 卡牌数 + 预期耗时),
不再返回 min_gpu_mb(那是旧硬件档位语义)。
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.proto.engine import run_forge
from app.proto.ritual import RITUALS, Ritual, get_ritual
from app.schemas import ForgeRequest, ForgeResponse, RitualInfo

router = APIRouter(prefix="/api/forge", tags=["forge"])


# 4 档定义(直接读 ritual.py 的 RITUALS,字段映射给前端 RitualInfo)
def _ritual_to_info(spec) -> RitualInfo:
    return RitualInfo(
        ritual=spec.name.value,
        description=(
            f"{spec.display_name} | {spec.difficulty}★ | "
            f"耗时 {spec.min_duration_sec}-{spec.max_duration_sec}s | "
            f"卡牌 {spec.cards_complexity} 张 | 徽章「{spec.badge}」"
        ),
        min_gpu_mb=0,  # 4 档不与硬件挂钩,这里填 0 保持 schema 兼容
        models=[],  # 难度模式不绑定具体模型
    )


_RITUAL_CATALOG: list[RitualInfo] = [_ritual_to_info(s) for s in RITUALS.values()]


def _forge_result_to_response(result) -> ForgeResponse:
    return ForgeResponse(
        run_id=result.run_id,
        mission_id=result.mission_id,
        ritual=result.ritual,
        ritual_used=result.ritual_used,
        duration_estimate_sec=result.duration_estimate_sec,
        duration_ms=result.duration_ms,
        badge_unlocked=result.badge_unlocked,
        intron=result.intron,
        fasta=result.fasta,
        scores=result.scores,
        risk_flags=result.risk_flags,
        passed_gate=result.passed_gate,
    )


@router.post("/run", response_model=ForgeResponse)
def forge_run(req: ForgeRequest) -> ForgeResponse:
    params = dict(req.params)
    if req.natural_language and req.natural_language.strip():
        from app.missions import get_mission
        from app.translate import translate

        try:
            mission = get_mission(req.mission_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        translated, _explanation = translate(req.natural_language, mission)
        # NL 翻译结果覆盖 params(玩家明确意图优先)
        params.update(translated)

    # 玩家主动选的 ritual(默认 urgent)。**不再**读 detect_hardware
    try:
        result = run_forge(req.mission_id, params, req.generator, req.seed, ritual=req.ritual)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _forge_result_to_response(result)


@router.get("/ritual", response_model=list[RitualInfo])
def forge_ritual() -> list[RitualInfo]:
    """返回所有仪式档位定义(供前端仪式选择器用)。"""
    return list(_RITUAL_CATALOG)


@router.get("/ritual/recommend", response_model=RitualInfo)
def forge_ritual_recommend() -> RitualInfo:
    """启动时推荐的档位 — 固定返回最低档(急锻),不再根据硬件推荐。

    玩家在 Settings 主动切换;启动时不替玩家做难度决策。
    """
    default = get_ritual(Ritual.urgent.value)
    return _ritual_to_info(default)
