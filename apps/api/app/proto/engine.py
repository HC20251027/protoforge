"""Proto 引擎封装。

Phase 1:不直接 import proto-language(它要 micromamba + 一堆生物模型),用启发式生成
内含子序列 + 内置评分器即可验证玩法。Phase 1.5 再接真 proto-language。
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
from .profile import detect_hardware
from app.config import settings


@dataclass
class ForgeResult:
    run_id: str
    mission_id: str
    ritual: str
    duration_ms: int
    intron: str
    fasta: str
    scores: dict
    risk_flags: list = field(default_factory=list)
    passed_gate: bool = False


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
) -> tuple[str, dict]:
    """简化的 Metropolis-Hastings 搜索:生成初始 -> 迭代突变 -> 取最优。"""
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

    for _ in range(steps):
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

    return best_seq, best_raw


def run_forge(mission_id: str, params: dict, generator: str, seed: int | None = None) -> ForgeResult:
    """端到端跑一次 forge(生成 + 评分 + 仪式名)。"""
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

    start = time.perf_counter()
    mcmc_steps = int(params.get("mcmc_steps", 50))
    if mcmc_steps <= 1:
        intron = _generate_intron(length, generator, seed)
        raw = score_intron(intron, min_target_splice=min_target, max_off_target_splice=max_off)
    else:
        intron, raw = _mcmc_search(length, generator, seed, mcmc_steps, params)

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
    hw = detect_hardware()

    return ForgeResult(
        run_id=f"run_{int(time.time() * 1000)}",
        mission_id=mission_id,
        ritual=hw.recommended_ritual,
        duration_ms=elapsed,
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
    )


def run_polar_glow(params: dict, generator: str = "preference", seed: int | None = None) -> ForgeResult:
    return run_forge("polar-glow-v1", params, generator, seed)
