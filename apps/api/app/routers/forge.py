"""Forge 路由:生成 + 评分 + 仪式推荐。"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.proto.engine import run_forge
from app.proto.profile import detect_hardware, recommend_ritual
from app.schemas import ForgeRequest, ForgeResponse, RitualInfo

router = APIRouter(prefix="/api/forge", tags=["forge"])


_RITUAL_CATALOG: list[RitualInfo] = [
    RitualInfo(
        ritual="swift",
        description="高速档:大显存 GPU + 轻量模型(ESM2-150M),秒级迭代。",
        min_gpu_mb=24_000,
        models=["ESM2-150M", "SpliceAI"],
    ),
    RitualInfo(
        ritual="standard",
        description="标准档:8-24GB GPU,SpliceTransformer 走 1 轮。",
        min_gpu_mb=8_000,
        models=["SpliceTransformer-base", "ESM2-650M"],
    ),
    RitualInfo(
        ritual="ancient",
        description="古法档:4-8GB GPU,纯 CPU 启发式 + 候选采样。",
        min_gpu_mb=4_000,
        models=["HeuristicScorer"],
    ),
    RitualInfo(
        ritual="crystal",
        description="水晶档:无 GPU,纯 CPU 启发式,可离线。",
        min_gpu_mb=0,
        models=["HeuristicScorer"],
    ),
]


def _forge_result_to_response(result) -> ForgeResponse:
    return ForgeResponse(
        run_id=result.run_id,
        mission_id=result.mission_id,
        ritual=result.ritual,
        duration_ms=result.duration_ms,
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

    try:
        result = run_forge(req.mission_id, params, req.generator, req.seed)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _forge_result_to_response(result)


@router.get("/ritual", response_model=list[RitualInfo])
def forge_ritual() -> list[RitualInfo]:
    """返回所有仪式档位定义(供前端仪式选择器用)。"""
    return list(_RITUAL_CATALOG)


@router.get("/ritual/recommend", response_model=RitualInfo)
def forge_ritual_recommend() -> RitualInfo:
    """根据当前硬件自动推荐一个仪式。"""
    hw = detect_hardware()
    recommended = recommend_ritual(hw.gpu_memory_mb)
    for item in _RITUAL_CATALOG:
        if item.ritual == recommended:
            return item
    return _RITUAL_CATALOG[-1]
