"""Proto 引擎封装。

Phase 1:不直接 import proto-language(它要 micromamba + 一堆生物模型),用启发式生成
内含子序列 + 内置评分器即可验证玩法。Phase 1.5 再接真 proto-language。
"""
from __future__ import annotations
import time
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
    """生成候选内含子序列(启发式,Phase 1 不接真 proto-language)。"""
    rng = random.Random(seed)
    if generator == "uniform":
        return "".join(rng.choices("ATGC", k=length))
    if generator == "random":
        return "".join(rng.choices("ATGC", k=length))
    # preference: GT-AG 边界,中段高熵
    seq = list(rng.choices("ATGC", k=length))
    if length >= 6:
        seq[0:2] = list("GT")
        seq[-2:] = list("AG")
    return "".join(seq)


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
    intron = _generate_intron(length, generator, seed)
    raw = score_intron(intron, min_target_splice=min_target, max_off_target_splice=max_off)

    primary = round(
        w_alpha * raw["splice_site_score"]
        + w_beta * (1.0 - raw["orthogonality"])
        - weights["gc_penalty"] * raw["gc_penalty"]
        - weights["length_penalty"] * raw["length_norm"],
        3,
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
