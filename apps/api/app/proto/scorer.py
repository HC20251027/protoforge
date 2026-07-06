"""序列评分器(CPU 可跑的启发式评分)。"""
from __future__ import annotations
import re
import math
from collections import Counter


def _gc_content(seq: str) -> float:
    if not seq:
        return 0.0
    seq = seq.upper()
    gc = sum(1 for c in seq if c in "GC")
    return gc / len(seq)


def _kmer_entropy(seq: str, k: int = 3) -> float:
    if len(seq) < k:
        return 0.0
    kmers = [seq[i:i + k] for i in range(len(seq) - k + 1)]
    counts = Counter(kmers)
    total = sum(counts.values())
    return -sum((c / total) * math.log2(c / total) for c in counts.values())


def _splice_site_score(seq: str) -> float:
    """简化版剪接位点评分:GT-AG 边界 + 周围上下文。

    真生产应调 SpliceTransformer;此处用 motif 启发式确保无依赖也能跑。
    """
    seq = seq.upper()
    donor = len(re.findall(r"[A-Z]G[CT]A[AG][CT]T", seq[:60]))
    acceptor = len(re.findall(r"[CT]AG[AG][A-Z]{15,20}G", seq[-60:]))
    branch = len(re.findall(r"[CT]T[AG]A[CT]", seq))
    score = min(1.0, (donor * 0.4 + acceptor * 0.4 + branch * 0.05))
    return score


def score_intron(intron: str, *, min_gc: float = 0.35, max_gc: float = 0.65,
                 min_target_splice: float = 0.65, max_off_target_splice: float = 0.20) -> dict:
    """评分内含子,返回各组件 + 综合分。"""
    gc = _gc_content(intron)
    splice = _splice_site_score(intron)
    ent = _kmer_entropy(intron, k=3) / 2.5
    ent = max(0.0, min(1.0, ent))

    gc_penalty = max(0.0, max(gc - max_gc, min_gc - gc))
    length_norm = min(1.0, len(intron) / 200.0)

    orthogonality = max(0.0, min(1.0, 0.5 * ent + 0.3 * (1.0 - splice) + 0.2 * (1.0 - gc_penalty * 2)))

    passed = splice >= min_target_splice and orthogonality <= max_off_target_splice + 0.1
    return {
        "gc_content": round(gc, 3),
        "splice_site_score": round(splice, 3),
        "orthogonality": round(orthogonality, 3),
        "kmer_entropy": round(ent, 3),
        "gc_penalty": round(gc_penalty, 3),
        "length_norm": round(length_norm, 3),
        "passes_thresholds": passed,
    }


def score_sequence(seq: str) -> dict:
    return {
        "gc_content": round(_gc_content(seq), 3),
        "kmer_entropy": round(_kmer_entropy(seq), 3),
    }
