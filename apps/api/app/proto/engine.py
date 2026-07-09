"""Proto 引擎封装。

Phase 1:不直接 import proto-language(它要 micromamba + 一堆生物模型),用启发式生成
内含子序列 + 内置评分器即可验证玩法。Phase 1.5 再接真 proto-language。

Phase 3 Task 2:4 档难度由玩家主动选择(ritual.py),与硬件解耦。
Phase 3 Task 3:退出惩罚 — run_forge 通过 RitualStateStore 写进度,
应用启动时 recover_unfinished_runs() 处理上次未完成的。

Phase 3 Task 6 P0-A2:显式失败 — 之前 MCMC step 抛错时,内层 except
会"静默退化"成默认分(score=0),玩家分不清"算法没找到好序列"和
"算法崩了"。修复:内层错误包成 `ForgeExecutionError`,顶层 catch 后
把错误消息塞进 `result.errors: list[str]`,HTTP 仍 200 返回(让玩家
能继续),前端用 errors 是否非空决定要不要显示"⚠️ 计算异常"横幅。
"""
from __future__ import annotations
import time
import math
import random
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any

from .scorer import score_intron
from .ritual import RitualSpec, default_ritual, get_ritual
from .ritual_state import (
    RitualStateStore,
    RitualRunState,
    get_default_store,
)
from app.config import settings


class ForgeExecutionError(RuntimeError):
    """Phase 3 Task 6 P0-A2:`run_forge` 内部任何异常都包成这个,顶层 catch
    后写入 `result.errors` — 显式失败,不静默退化。"""


@dataclass
class ForgeResult:
    run_id: str
    mission_id: str
    ritual: str
    ritual_used: str
    duration_ms: int
    duration_estimate_sec: int
    badge_unlocked: str | None
    intron: str
    fasta: str
    scores: dict
    risk_flags: list = field(default_factory=list)
    passed_gate: bool = False
    # Phase 3 Task 6 P0-A2:运行过程中产生的错误信息(默认空 = 成功)
    errors: list[str] = field(default_factory=list)


_TEMPLATES_DIR = Path(__file__).parent / "templates"


def _load_template(mission_id: str) -> dict:
    """加载任务模板。Phase 1 只支持 polar-glow-v1。"""
    if mission_id == "polar-glow-v1":
        with open(_TEMPLATES_DIR / "polar-glow.json", "r", encoding="utf-8") as f:
            return json.load(f)
    raise ValueError(f"Unknown mission_id: {mission_id}")


def _generate_intron(length: int, generator: str, seed: int | None) -> str:
    """生成候选内含子序列(三种模式各有不同的统计特征)。"""
    rng = random.Random(seed)
    if generator == "uniform":
        # 完全均匀:等概率 ATGC
        return "".join(rng.choices("ATGC", k=length))
    if generator == "random":
        # 偏 GC 分布(模拟基因组高 GC 区段)
        # weights 对应 "ATGC": A=0.2, T=0.2, G=0.3, C=0.3 -> GC=0.6, AT=0.4
        return "".join(rng.choices("ATGC", weights=[0.2, 0.2, 0.3, 0.3], k=length))
    # preference: GT-AG 边界 + 中段高熵
    seq = list(rng.choices("ATGC", k=length))
    if length >= 6:
        seq[0:2] = list("GT")
        seq[-2:] = list("AG")
    return "".join(seq)


def _mutate(seq: str, rng: random.Random, rate: float = 0.05) -> str:
    """单点突变:随机替换 rate 比例的碱基。"""
    bases = list(seq)
    n = max(1, int(len(bases) * rate))
    for _ in range(n):
        i = rng.randint(0, len(bases) - 1)
        bases[i] = rng.choice("ATGC")
    return "".join(bases)


def _mcmc_search(
    length: int,
    generator: str,
    seed: int | None,
    steps: int,
    params: dict,
    on_progress=None,
) -> tuple[str, dict]:
    """简化的 Metropolis-Hastings 搜索:生成初始 -> 迭代突变 -> 取最优。

    Args:
        on_progress: 可选回调 on_progress(step: int) — 用来把进度写到
                     RitualStateStore(Phase 3 Task 3 退出惩罚用)。
    """
    rng = random.Random(seed)
    min_target = float(params.get("min_target_splice", 0.65))
    max_off = float(params.get("max_off_target", 0.20))
    w_alpha = float(params.get("weight_alpha", 0.5))
    w_beta = float(params.get("weight_beta", 0.35))

    best_seq = _generate_intron(length, generator, seed)
    best_raw = score_intron(best_seq, min_target_splice=min_target, max_off_target_splice=max_off)
    best_primary = max(
        0.0,
        w_alpha * best_raw["splice_site_score"]
        + w_beta * (1.0 - best_raw["orthogonality"])
        - 0.1 * best_raw["gc_penalty"]
        - 0.05 * best_raw["length_norm"],
    )

    current_seq = best_seq
    current_primary = best_primary
    temp = float(params.get("temperature", 0.8))

    # Phase 3 Task 3:每 10% step 回调一次 on_progress(节流,避免 IO 风暴)
    next_progress_marker = max(1, steps // 10) if steps > 0 else 1

    for step in range(steps):
        candidate = _mutate(current_seq, rng, rate=0.05)
        raw = score_intron(candidate, min_target_splice=min_target, max_off_target_splice=max_off)
        primary = max(
            0.0,
            w_alpha * raw["splice_site_score"]
            + w_beta * (1.0 - raw["orthogonality"])
            - 0.1 * raw["gc_penalty"]
            - 0.05 * raw["length_norm"],
        )
        # Metropolis 接受准则
        delta = primary - current_primary
        if delta > 0 or (temp > 0 and rng.random() < math.exp(delta / max(temp, 0.001))):
            current_seq = candidate
            current_primary = primary
        if primary > best_primary:
            best_seq = candidate
            best_raw = raw
            best_primary = primary

        # 节流回调:每 10% 一次 + 最后一步
        if on_progress is not None and (
            (step + 1) % next_progress_marker == 0 or (step + 1) == steps
        ):
            try:
                on_progress(step + 1)
            except Exception:  # noqa: BLE001
                # 回调失败不能让 MCMC 崩
                pass

    return best_seq, best_raw


def run_forge(
    mission_id: str,
    params: dict,
    generator: str,
    seed: int | None = None,
    ritual: str = "urgent",
    state_store: RitualStateStore | None = None,
) -> ForgeResult:
    """端到端跑一次 forge(生成 + 评分 + 仪式名)。

    Args:
        mission_id: 任务模板 ID
        params: 可调参数(滑块等)
        generator: 序列生成模式(uniform / random / preference)
        seed: 随机种子(可复现)
        ritual: 锻炉档位(玩家主动选,默认 urgent/急锻)
        state_store: Phase 3 Task 3 用 — 持久化 run 进度。
                     传 None 时走 default singleton(自动写盘)。

    Returns:
        ForgeResult:包含 intron / fasta / 评分 / 仪式名 / 徽章
    """
    tpl = _load_template(mission_id)
    proto_tpl = tpl["proto_template"]
    weights = proto_tpl["scoring"]["weights"]
    min_target = float(params.get("min_target_splice", proto_tpl["constraint"]["min_target_splice_score"]))
    max_off = float(params.get("max_off_target", proto_tpl["constraint"]["max_off_target_splice_score"]))
    w_alpha = float(params.get("weight_alpha", weights["target_splice"]))
    w_beta = float(params.get("weight_beta", weights["orthogonality"]))
    length = int(proto_tpl["intron_length_range"][0] +
                 (proto_tpl["intron_length_range"][1] - proto_tpl["intron_length_range"][0]) * 0.5)
    length = max(80, min(250, length))

    # 玩家主动选的 ritual 决定 MCMC 步数(与硬件解耦,这是"决策密度")
    spec: RitualSpec = get_ritual(ritual)
    # 允许 params 覆盖(向后兼容旧的 mcmc_steps 入口),但默认走 spec.calculation_steps
    mcmc_steps = int(params.get("mcmc_steps", spec.calculation_steps))
    mcmc_steps = max(1, mcmc_steps)

    # Phase 3 Task 3:start a run, get run_id, install on_progress callback
    store = state_store if state_store is not None else get_default_store()
    run_state: RitualRunState = store.start(ritual)
    run_id = run_state.run_id

    def _on_progress(step: int) -> None:
        # 容错:store.update 失败不能让 MCMC 崩
        try:
            store.update(run_id, step)
        except Exception:  # noqa: BLE001
            pass

    # Phase 3 Task 6 P0-A2:收集错误用(顶层 handler 把 ForgeExecutionError
    # 写回 result.errors,不让 MCMC 异常静默退化成 score=0)
    collected_errors: list[str] = []

    start = time.perf_counter()
    try:
        if mcmc_steps <= 1:
            intron = _generate_intron(length, generator, seed)
            raw = score_intron(intron, min_target_splice=min_target, max_off_target_splice=max_off)
            # mcmc_steps=1 路径也标记当前 step
            _on_progress(mcmc_steps)
        else:
            intron, raw = _mcmc_search(length, generator, seed, mcmc_steps, params, on_progress=_on_progress)
    except Exception as exc:  # noqa: BLE001
        # P0-A2 修复:不再静默退化成 score=0。把错误记到 result.errors,
        # 并生成一个**最小可用**的 intron(空序列 + 默认 raw),让玩家
        # UI 仍能继续(但 result.passed_gate=False 且 errors 非空)。
        error_msg = f"{type(exc).__name__}: {exc}"
        collected_errors.append(f"MCMC 搜索失败 ({error_msg})")
        intron = ""
        raw = {
            "splice_site_score": 0.0,
            "orthogonality": 0.0,
            "gc_penalty": 0.0,
            "length_norm": 0.0,
            "kmer_entropy": 0.0,
            "passes_thresholds": False,
        }
        # 标完进度,让 RitualStateStore 知道这次 run 结束了
        try:
            _on_progress(mcmc_steps)
        except Exception:  # noqa: BLE001
            pass

    primary = max(
        0.0,
        round(
            w_alpha * raw["splice_site_score"]
            + w_beta * (1.0 - raw["orthogonality"])
            - weights["gc_penalty"] * raw["gc_penalty"]
            - weights["length_penalty"] * raw["length_norm"],
            3,
        ),
    )

    risk_flags = []
    if not raw["passes_thresholds"]:
        risk_flags.append({
            "rule_id": "thresholds",
            "severity": "warn",
            "message": f"未达剪接/正交阈值 (splice={raw['splice_site_score']:.2f}, ortho={raw['orthogonality']:.2f})",
        })

    elapsed = int((time.perf_counter() - start) * 1000)
    fasta = f">protoforge_{mission_id}\n{intron}\n"

    # P0-A2:即使 MCMC 失败,passed_gate 也必须 = False(因为 raw 是默认 0 分)
    result = ForgeResult(
        run_id=run_id,
        mission_id=mission_id,
        ritual=spec.name.value,
        ritual_used=spec.name.value,
        duration_ms=elapsed,
        duration_estimate_sec=spec.max_duration_sec,
        badge_unlocked=spec.badge,
        intron=intron,
        fasta=fasta,
        scores={
            "primary": primary,
            "components": {
                "target_splice": raw["splice_site_score"],
                "orthogonality": raw["orthogonality"],
                "gc_penalty": raw["gc_penalty"],
                "length_penalty": raw["length_norm"],
                "kmer_entropy": raw["kmer_entropy"],
            },
            "weights": {"alpha": w_alpha, "beta": w_beta},
        },
        risk_flags=risk_flags,
        passed_gate=raw["passes_thresholds"],
        errors=collected_errors,
    )

    # Phase 3 Task 3:标完成 + 存 result(让 KEEP_RESULT 路径生效)
    try:
        store.complete(run_id, _result_to_json(result))
    except Exception:  # noqa: BLE001
        # 写盘失败不能让 forge 失败(返回结果优先)
        pass

    return result


def _result_to_json(result: ForgeResult) -> dict:
    """把 ForgeResult 转成可序列化的 dict(给 ritual_state 存盘用)。"""
    return {
        "run_id": result.run_id,
        "mission_id": result.mission_id,
        "ritual": result.ritual,
        "ritual_used": result.ritual_used,
        "duration_ms": result.duration_ms,
        "duration_estimate_sec": result.duration_estimate_sec,
        "badge_unlocked": result.badge_unlocked,
        "intron": result.intron,
        "fasta": result.fasta,
        "scores": result.scores,
        "risk_flags": result.risk_flags,
        "passed_gate": result.passed_gate,
        "errors": result.errors,
    }


def recover_unfinished_runs(
    state_store: RitualStateStore | None = None,
) -> list[ForgeResult]:
    """应用启动时调一次,处理上次未完成的 run。

    对每个 status in (running, lost) 的 run:
    * running → evaluate_exit_on_return(可能标 lost)
    * 已经是 lost 的 → 跳过(只查不写)

    Returns:
        list[ForgeResult]: 本次启动时**保留**的 run(KEEP_RESULT)。
        这些可以放回"未完成"列表(虽然已算完)。
    """
    store = state_store if state_store is not None else get_default_store()
    kept: list[ForgeResult] = []
    for state in store.list_unfinished():
        # 只处理 running 状态(已 lost 的不动)
        if state.status != "running":
            continue
        outcome = store.evaluate_exit_on_return(state.run_id)
        if outcome.value == "keep":
            # 没找到对应 result(因为上次退出时没存 result)
            # 这里不强行 forge 一次 — 只标完成 + 返回最小 ForgeResult
            # (如果玩家想要完整 result,需要重新跑)
            kept.append(ForgeResult(
                run_id=state.run_id,
                mission_id="unknown",  # 上次 run 没存 mission_id
                ritual=state.ritual,
                ritual_used=state.ritual,
                duration_ms=0,
                duration_estimate_sec=0,
                badge_unlocked=None,
                intron="",
                fasta="",
                scores={"primary": 0.0, "components": {}, "weights": {}},
                risk_flags=[],
                passed_gate=False,
            ))
    return kept


def run_polar_glow(
    params: dict,
    generator: str = "preference",
    seed: int | None = None,
    ritual: str = "urgent",
    state_store: RitualStateStore | None = None,
) -> ForgeResult:
    return run_forge("polar-glow-v1", params, generator, seed, ritual=ritual, state_store=state_store)
