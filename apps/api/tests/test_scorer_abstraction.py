"""Task 4: 评分器抽象层测试。

覆盖点:
- HeuristicScorer 直接调用返回标准键
- score_intron 兼容层包含新加的 `_scorer` 字段
- get_scorer() 单例 + 模式切换
- SpliceTransformerScorer 在无 torch 时回退
"""
import os

import pytest

from app.proto.scorer import (
    HeuristicScorer,
    Scorer,
    SpliceTransformerScorer,
    get_scorer,
    score_intron,
)


@pytest.fixture(autouse=True)
def _reset_scorer_cache():
    """每个用例前后清空单例,确保环境变量切换能生效。"""
    from app.proto import scorer as scorer_mod

    scorer_mod._cached = None
    yield
    scorer_mod._cached = None


def test_heuristic_scorer_implements_interface():
    s = HeuristicScorer()
    assert isinstance(s, Scorer)
    assert s.name == "heuristic"


def test_heuristic_score_returns_required_keys():
    s = HeuristicScorer()
    out = s.score("ATGCGT" * 10)
    assert "gc_content" in out
    assert "splice_site_score" in out
    assert "kmer_entropy" in out
    assert 0.0 <= out["splice_site_score"] <= 1.0


def test_score_intron_includes_scorer_name():
    out = score_intron("ATGCGT" * 20)
    assert out["_scorer"] == "heuristic"
    # 兼容层必须包含旧字段(向后兼容)
    for key in (
        "gc_content",
        "splice_site_score",
        "orthogonality",
        "kmer_entropy",
        "gc_penalty",
        "length_norm",
        "passes_thresholds",
    ):
        assert key in out, f"missing key: {key}"


def test_get_scorer_singleton():
    a = get_scorer()
    b = get_scorer()
    assert a is b
    assert a.name == "heuristic"


def test_get_scorer_falls_back_when_transformer_unavailable(monkeypatch, capsys):
    """无 torch 时,PROTOFORGE_SPLICER=transformer 应回退到启发式并打印警告。"""
    monkeypatch.setenv("PROTOFORGE_SPLICER", "transformer")

    # 强制构造时抛 RuntimeError,模拟无 torch
    def _boom(*args, **kwargs):
        raise RuntimeError("torch not installed")

    monkeypatch.setattr(
        "app.proto.scorer.SpliceTransformerScorer.__init__", _boom
    )
    s = get_scorer()
    assert s.name == "heuristic"
    captured = capsys.readouterr()
    assert "transformer 不可用" in captured.out


def test_splice_transformer_scorer_runs_without_torch():
    """SpliceTransformerScorer 不应再抛 NotImplementedError。

    当前实装:不依赖 torch,使用 numpy + PWM(位置权重矩阵)做 donor/acceptor 打分。
    """
    s = SpliceTransformerScorer()
    out = s.score("ATGCGT" * 10)
    assert "splice_site_score" in out
    assert 0.0 <= out["splice_site_score"] <= 1.0


def test_splice_transformer_prefers_real_splice_motifs():
    """真实 GT-AG 边界序列的剪接分应高于纯随机序列。"""
    s = SpliceTransformerScorer()
    good = "GT" + "ATGCATGC" * 8 + "AG"  # 强 donor/acceptor
    bad = "ATGCATGC" * 10                 # 无 motif
    g_score = s.score(good)["splice_site_score"]
    b_score = s.score(bad)["splice_site_score"]
    assert g_score > b_score, f"GT-AG 序列分({g_score})应高于随机({b_score})"
