"""序列评分器抽象层 + 默认启发式实现。

设计原则:
- 侧车进程不依赖任何 ML 框架(避免 torch 启动开销)。
- `SpliceTransformerScorer` 是接口占位:如果用户安装了 `spliceai`/`splice-transformer`,
  可以通过环境变量 `PROTOFORGE_SPLICER=transformer` 启用,否则自动回退到启发式。
- 这样 Phase 1 的侧车始终可启动,Phase 2 再补真实模型。
"""
from __future__ import annotations

import os
import re
import math
from abc import ABC, abstractmethod
from collections import Counter
from dataclasses import dataclass


class Scorer(ABC):
    """统一的剪接位点评分器接口。"""

    name: str = "abstract"

    @abstractmethod
    def score(self, seq: str) -> dict:
        """评分一段内含子,返回 0~1 区间的剪接位点强度 + 旁路特征。"""


# ---------------------------------------------------------------------------
# HeuristicScorer(默认,纯 Python)
# ---------------------------------------------------------------------------

class HeuristicScorer(Scorer):
    """基于 motif 的启发式评分器,CPU 即时跑通。"""

    name = "heuristic"

    def __init__(self) -> None:
        # 预编译正则,避免重复解析
        self._donor_re = re.compile(r"[A-Z]G[CT]A[AG][CT]T")
        self._acceptor_re = re.compile(r"[CT]AG[AG][A-Z]{15,20}G")
        self._branch_re = re.compile(r"[CT]T[AG]A[CT]")

    def _gc_content(self, seq: str) -> float:
        if not seq:
            return 0.0
        seq = seq.upper()
        gc = sum(1 for c in seq if c in "GC")
        return gc / len(seq)

    def _kmer_entropy(self, seq: str, k: int = 3) -> float:
        if len(seq) < k:
            return 0.0
        kmers = [seq[i:i + k] for i in range(len(seq) - k + 1)]
        counts = Counter(kmers)
        total = sum(counts.values())
        return -sum((c / total) * math.log2(c / total) for c in counts.values())

    def score(self, seq: str) -> dict:
        seq = seq.upper()
        donor = len(self._donor_re.findall(seq[:60]))
        acceptor = len(self._acceptor_re.findall(seq[-60:]))
        branch = len(self._branch_re.findall(seq))
        splice = min(1.0, donor * 0.4 + acceptor * 0.4 + branch * 0.05)
        return {
            "gc_content": round(self._gc_content(seq), 3),
            "splice_site_score": round(splice, 3),
            "kmer_entropy": round(self._kmer_entropy(seq) / 2.5, 3),
        }


# ---------------------------------------------------------------------------
# SpliceTransformerScorer(可选,接口占位)
# ---------------------------------------------------------------------------

class SpliceTransformerScorer(Scorer):
    """Splice 位点评分器 — 简化版(无 torch 依赖)。

    实现:用位置权重矩阵(PWM)对 donor/acceptor 位点打分。
    - donor  位置窗口:序列前 6 nt(GT + 保守区)
    - acceptor 位置窗口:序列后 16 nt(polypyrimidine tract + AG)
    - 输出:归一化到 0~1 的剪接强度 + GC 含量 + 3-mer 熵

    论文里 real SpliceTransformer / SpliceAI 可作为 Phase 3 升级,
    接口不变,只换实现。
    """

    name = "transformer"

    # donor PWM(6 位置 × 4 碱基),行=位置,列=A/C/G/T 的 log-odds
    _DONOR_PWM = [
        {"G": 1.5, "A": 0.4, "C": -0.3, "T": 0.0},   # 5'ss -6
        {"G": 0.2, "A": 1.4, "C": -0.1, "T": 0.3},   # 5'ss -5
        {"G": 2.0, "A": -0.5, "C": -0.2, "T": 0.0},  # 5'ss -4 (G 必需)
        {"T": 1.8, "A": -0.3, "C": 0.0, "G": -0.4},  # 5'ss -3
        {"A": 1.3, "G": 0.5, "C": 0.0, "T": -0.2},   # 5'ss -2
        {"G": 1.6, "A": 0.2, "C": 0.0, "T": -0.3},   # 5'ss -1
    ]
    # acceptor PWM(15 位置),典型 YAG/RAN 模式
    _ACCEPTOR_PWM = [
        {"T": 0.8, "C": 0.7, "A": 0.2, "G": -0.1},  # -15
        {"T": 1.0, "C": 0.6, "A": 0.0, "G": -0.2},  # -14
        {"T": 0.9, "C": 0.7, "A": 0.1, "G": -0.1},  # -13
        {"T": 0.7, "C": 0.8, "A": 0.2, "G": -0.1},  # -12
        {"T": 0.6, "C": 0.9, "A": 0.2, "G": 0.0},   # -11
        {"T": 0.5, "C": 0.9, "A": 0.3, "G": 0.0},   # -10
        {"T": 0.4, "C": 0.8, "A": 0.4, "G": 0.1},   # -9
        {"T": 0.3, "C": 0.7, "A": 0.5, "G": 0.2},   # -8
        {"T": 0.2, "C": 0.5, "A": 0.6, "G": 0.4},   # -7
        {"C": 0.3, "T": 0.2, "A": 0.4, "G": 0.5},   # -6
        {"A": 0.3, "C": 0.2, "T": 0.3, "G": 0.5},   # -5
        {"A": 0.2, "C": 0.1, "T": 0.3, "G": 0.6},   # -4
        {"A": 0.1, "T": 0.1, "C": 0.0, "G": 0.7},   # -3
        {"A": 0.0, "T": 0.0, "C": 0.0, "G": 0.8},   # -2
        {"G": 1.5, "A": 0.2, "T": 0.0, "C": -0.2},  # -1
    ]

    def __init__(self, model_id: str | None = None) -> None:
        # Phase 2 简化实现不依赖 torch;若 Phase 3 装上 torch,
        # 可在这里 `import torch` + 加载真实模型,接口不变。
        self._model_id = model_id or "pwm-baseline"

    def _pwm_score(self, window: str, pwm: list[dict]) -> float:
        """位置权重矩阵打分:sum of log-odds,归一化到 0~1。"""
        window = window.upper()
        if len(window) < len(pwm):
            return 0.0
        raw = 0.0
        for i, base in enumerate(window[:len(pwm)]):
            raw += pwm[i].get(base, -1.0)
        # 归一化:理论 max = sum(max in each position)
        max_score = sum(max(row.values()) for row in pwm)
        return max(0.0, min(1.0, raw / max_score))

    def _gc(self, seq: str) -> float:
        if not seq:
            return 0.0
        s = seq.upper()
        return sum(1 for c in s if c in "GC") / len(s)

    def _kmer_entropy(self, seq: str, k: int = 3) -> float:
        if len(seq) < k:
            return 0.0
        kmers = [seq[i:i + k] for i in range(len(seq) - k + 1)]
        counts: dict[str, int] = {}
        for kmer in kmers:
            counts[kmer] = counts.get(kmer, 0) + 1
        total = sum(counts.values())
        import math
        return -sum((c / total) * math.log2(c / total) for c in counts.values())

    def score(self, seq: str) -> dict:
        seq = seq.upper()
        donor = self._pwm_score(seq[:6], self._DONOR_PWM)
        acceptor = self._pwm_score(seq[-15:], self._ACCEPTOR_PWM)
        splice = min(1.0, 0.55 * donor + 0.55 * acceptor)
        return {
            "gc_content": round(self._gc(seq), 3),
            "splice_site_score": round(splice, 3),
            "kmer_entropy": round(self._kmer_entropy(seq) / 2.5, 3),
        }


# ---------------------------------------------------------------------------
# 工厂 + 单例缓存
# ---------------------------------------------------------------------------

_cached: Scorer | None = None


def get_scorer() -> Scorer:
    """根据环境变量选择评分器(单例)。"""
    global _cached
    if _cached is not None:
        return _cached
    mode = (os.environ.get("PROTOFORGE_SPLICER") or "heuristic").lower()
    if mode == "transformer":
        try:
            _cached = SpliceTransformerScorer()
            return _cached
        except RuntimeError as exc:
            # 回退到启发式,记录一行警告便于排查
            print(f"[proto] transformer 不可用,回退启发式: {exc}")
    _cached = HeuristicScorer()
    return _cached


# ---------------------------------------------------------------------------
# 兼容层(供 engine.py 调用的 legacy API)
# ---------------------------------------------------------------------------

@dataclass
class ScoreThresholds:
    min_gc: float = 0.35
    max_gc: float = 0.65
    min_target_splice: float = 0.65
    max_off_target_splice: float = 0.20


def score_intron(
    intron: str,
    *,
    min_gc: float = 0.35,
    max_gc: float = 0.65,
    min_target_splice: float = 0.65,
    max_off_target_splice: float = 0.20,
) -> dict:
    """评分内含子,返回各组件 + 综合分(向后兼容的入口函数)。"""
    scorer = get_scorer()
    base = scorer.score(intron)
    gc = base.get("gc_content", 0.0)
    splice = base.get("splice_site_score", 0.0)
    ent = base.get("kmer_entropy", 0.0)

    gc_penalty = max(0.0, max(gc - max_gc, min_gc - gc))
    length_norm = min(1.0, len(intron) / 200.0)

    orthogonality = max(
        0.0,
        min(1.0, 0.5 * ent + 0.3 * (1.0 - splice) + 0.2 * (1.0 - gc_penalty * 2)),
    )

    passed = splice >= min_target_splice and orthogonality <= max_off_target_splice + 0.1
    return {
        "gc_content": round(gc, 3),
        "splice_site_score": round(splice, 3),
        "orthogonality": round(orthogonality, 3),
        "kmer_entropy": round(ent, 3),
        "gc_penalty": round(gc_penalty, 3),
        "length_norm": round(length_norm, 3),
        "passes_thresholds": passed,
        "_scorer": scorer.name,
    }


def score_sequence(seq: str) -> dict:
    return get_scorer().score(seq)
