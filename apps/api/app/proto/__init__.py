"""Proto-language 引擎:硬件感知 + 启发式评分 + 任务模板。

Phase 1 全部 CPU 可跑,Phase 2 接入 SpliceTransformer/ESM2/AlphaGenome。
"""
from .engine import ForgeResult, run_forge, run_polar_glow
from .profile import HardwareProfile, detect_hardware, recommend_ritual
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
    "HardwareProfile",
    "detect_hardware",
    "recommend_ritual",
    "Scorer",
    "HeuristicScorer",
    "SpliceTransformerScorer",
    "ScoreThresholds",
    "get_scorer",
    "score_intron",
    "score_sequence",
]
