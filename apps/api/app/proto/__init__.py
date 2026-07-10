"""Proto-language 引擎:启发式评分 + 任务模板。

Phase 1 全部 CPU 可跑,Phase 2 接入 SpliceTransformer/ESM2/AlphaGenome。
Phase 4 A3:删 detect_hardware 残留,4 档按难度不按硬件划分。
"""
from .engine import ForgeResult, run_forge, run_polar_glow
from .scorer import (
    HeuristicScorer,
    Scorer,
    ScoreThresholds,
    SpliceTransformerScorer,
    get_scorer,
    score_intron,
    score_sequence,
)

__all__ = [
    "ForgeResult",
    "run_forge",
    "run_polar_glow",
    "Scorer",
    "HeuristicScorer",
    "SpliceTransformerScorer",
    "ScoreThresholds",
    "get_scorer",
    "score_intron",
    "score_sequence",
]
