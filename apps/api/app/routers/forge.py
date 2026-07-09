"""Forge 路由:生成 + 评分 + 仪式档位(Phase 3 Task 2) + 退出惩罚(Task 3)
+ Steam 创意工坊自动上传(Task 5)。

Phase 3 决策:4 档仪式**不与硬件挂钩**。玩家主动选择难度,系统不自动降级。
`/api/forge/ritual` 返回 4 档的"难度"维度(急锻者徽章 + 卡牌数 + 预期耗时),
不再返回 min_gpu_mb(那是旧硬件档位语义)。

Phase 3 Task 3 退出惩罚:
* `POST /api/forge/run` 现在返回 run_id
* `GET  /api/forge/unfinished` 列上次未完成的 run
* `POST /api/forge/exit-evaluate` 接受 run_id,evaluate 退出结果

Phase 3 Task 5 Steam 自动上传:
* `POST /api/forge/run` 通关后(risk_gate_passed + score >= threshold)
  → 自动 pack → enqueue → try upload
* 返回字段加 `upload: UploadStatus`(给前端 toast 用)
"""
from __future__ import annotations

import logging
import os

from fastapi import APIRouter, HTTPException

from app.proto.engine import run_forge
from app.proto.exit_penalty import evaluate_exit
from app.proto.ritual import RITUALS, Ritual, get_ritual
from app.proto.ritual_state import (
    RitualRunState,
    get_default_store,
)
from app.protoforge.packager import ProtoforgePackager
from app.protoforge.queue import (
    STATUS_FAILED,
    STATUS_QUEUED,
    UploadQueue,
)
from app.protoforge.steam import (
    get_default_uploader,
)
from app.schemas import (
    ExitEvaluationRequest,
    ExitEvaluationResponse,
    ForgeRequest,
    ForgeResponse,
    RitualInfo,
    UnfinishedRun,
    UploadStatus,
)

log = logging.getLogger("protoforge.forge")

# 玩家 ID 从环境变量取(本任务还没有 user system),默认 "default"
_DEFAULT_PLAYER_ID = "default"

# 通关上传触发阈值:ForgeResult.scores.primary >= 0.3
# 选择 0.3 的理由:polar-glow 模板下,典型合规 run 的 primary 范围是 0.3~0.8;
# 明显违规(脱离 motif)的 run 远低于 0.3。粗筛 — 真判定是 risk_gate_passed。
_UPLOAD_SCORE_THRESHOLD = 0.3

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


def _resolve_player_id() -> str:
    """从环境变量读 player_id(暂时没有 user system,本任务用 env 隔离玩家)。

    Phase 4 接 user system 时,改成读 JWT。
    """
    return os.environ.get("PROTOFORGE_PLAYER_ID", _DEFAULT_PLAYER_ID)


def _forge_result_to_response(result, upload: UploadStatus) -> ForgeResponse:
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
        upload=upload,
    )


def _state_to_unfinished(state: RitualRunState, outcome: str) -> UnfinishedRun:
    return UnfinishedRun(
        run_id=state.run_id,
        ritual=state.ritual,  # type: ignore[arg-type]
        current_step=state.current_step,
        total_steps=state.total_steps,
        started_at=state.started_at,
        outcome=outcome,  # type: ignore[arg-type]
    )


def _try_upload_after_pass(
    result,
    mission_id: str,
    ritual: str,
    player_id: str,
) -> UploadStatus:
    """通关后自动上传 hook(Phase 3 Task 5)。

    流程:
    1. packager.pack(result) → 写 .protoforge 文件
    2. queue.enqueue(export_path) → 入队
    3. uploader.is_steam_running() →
       - True:uploader.upload_item() → 标 uploaded
       - False:留 queued,玩家下次 retry

    任何步骤失败都不抛(通关成功是首要目标,上传是 bonus),
    失败时返回 UploadStatus(status="failed"/"queued", queued=True)。
    """
    try:
        # 1) 打包
        packager = ProtoforgePackager()
        pack = packager.pack(
            forge_result=result,
            mission_id=mission_id,
            ritual=ritual,
            player_id=player_id,
        )

        # 2) 入队
        q = UploadQueue.for_player(player_id)
        queue_id = q.enqueue(
            export_path=pack.file_path,
            mission_id=mission_id,
            ritual=ritual,
        )

        # 3) 尝试实时上传(Steam 运行中才试,否则保持 queued 等重试)
        uploader = get_default_uploader()
        if uploader.is_steam_running():
            try:
                title = f"{mission_id} · {ritual} · {result.badge_unlocked or '作品'}"
                description = (
                    f"ProtoForge 玩家作品 (run_id={result.run_id})\n"
                    f"任务:{mission_id} | 仪式:{ritual} | 评分:{result.scores['primary']:.3f}\n"
                    f"由 ProtoForge Phase 3 自动生成"
                )
                tags = ["protoforge", f"ritual-{ritual}", mission_id]
                workshop_id = uploader.upload_item(
                    file_path=pack.file_path,
                    title=title,
                    description=description,
                    tags=tags,
                )
                q.mark_uploaded(queue_id, workshop_id=workshop_id)
                return UploadStatus(
                    queued=True,
                    queue_id=queue_id,
                    workshop_id=workshop_id,
                    status="uploaded",
                    message=f"✅ 作品已上传到 Steam 创意工坊 (ID: {workshop_id})",
                )
            except Exception as exc:  # noqa: BLE001
                # 上传失败 → 标 failed(留队,可重试)
                log.warning("Steam 上传失败(留队重试): %s", exc)
                q.mark_failed(queue_id, error=str(exc))
                return UploadStatus(
                    queued=True,
                    queue_id=queue_id,
                    workshop_id=None,
                    status=STATUS_FAILED,
                    message=f"⚠️ 上传失败,已入待重试队列 ({exc})",
                )
        # Steam 没运行 → 留 queued
        return UploadStatus(
            queued=True,
            queue_id=queue_id,
            workshop_id=None,
            status=STATUS_QUEUED,
            message="📦 作品已入待上传队列(Steam 未运行,联网后自动重试)",
        )
    except Exception as exc:  # noqa: BLE001
        # 打包/入队失败也吞 — 通关结果优先
        log.warning("通关后上传流程失败: %s", exc)
        return UploadStatus(
            queued=False,
            queue_id=None,
            workshop_id=None,
            status="failed",
            message=f"⚠️ 作品存档失败 ({exc})",
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

    # Phase 3 Task 5:通关后自动上传 hook
    # 通关 = risk_gate_passed AND score >= threshold
    primary = float(result.scores.get("primary", 0.0))
    passed = bool(result.passed_gate) and primary >= _UPLOAD_SCORE_THRESHOLD

    if passed:
        upload = _try_upload_after_pass(
            result=result,
            mission_id=result.mission_id,
            ritual=result.ritual,
            player_id=_resolve_player_id(),
        )
    else:
        # 不通关 → 跳过上传
        upload = UploadStatus(
            queued=False,
            queue_id=None,
            workshop_id=None,
            status="skipped",
            message=(
                f"未达上传条件(risk_gate={result.passed_gate}, score={primary:.2f}, "
                f"需要 score >= {_UPLOAD_SCORE_THRESHOLD})"
            ),
        )

    return _forge_result_to_response(result, upload)


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


# ---------------------------------------------------------------------------
# Phase 3 Task 3:退出惩罚相关 endpoints
# ---------------------------------------------------------------------------

@router.get("/unfinished", response_model=list[UnfinishedRun])
def forge_unfinished() -> list[UnfinishedRun]:
    """返回所有未完成的 run(running + lost)。

    每个 run 都已经 evaluate 过(LOSE 标 lost,KEEP 仍 running — 等玩家来取结果)。
    """
    store = get_default_store()
    out: list[UnfinishedRun] = []
    for state in store.list_unfinished():
        if state.status == "lost":
            outcome = "lose"
        elif state.status == "running":
            # 仍在 running 的 → 重新 evaluate(防止 LOSE 还没标)
            ev_outcome = store.evaluate_exit_on_return(state.run_id)
            outcome = "keep" if ev_outcome.value == "keep" else "lose"
        else:
            # done — 跳过(不算 unfinished)
            continue
        out.append(_state_to_unfinished(state, outcome))
    return out


@router.post("/exit-evaluate", response_model=ExitEvaluationResponse)
def forge_exit_evaluate(req: ExitEvaluationRequest) -> ExitEvaluationResponse:
    """手动 evaluate 某 run 的退出结果(前端 resume 流程 + 调试用)。"""
    store = get_default_store()
    state = store.get(req.run_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"run_id not found: {req.run_id}")
    # 已经 done → 永远 KEEP
    if state.status == "done":
        return ExitEvaluationResponse(
            outcome="keep",
            ritual=state.ritual,  # type: ignore[arg-type]
            progress_ratio=1.0,
        )
    ev_outcome = store.evaluate_exit_on_return(req.run_id)
    progress = state.progress_ratio() if state.total_steps > 0 else 0.0
    return ExitEvaluationResponse(
        outcome=ev_outcome.value,  # type: ignore[arg-type]
        ritual=state.ritual,  # type: ignore[arg-type]
        progress_ratio=round(progress, 4),
    )
