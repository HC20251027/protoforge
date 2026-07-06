"""Forge 引擎 smoke 测试。"""
from app.proto.engine import run_forge, run_polar_glow
from app.proto.scorer import score_intron


def test_score_intron_basic() -> None:
    intron = "GTATGCATGC" + "ATGC" * 20 + "AG"
    res = score_intron(intron)
    assert "splice_site_score" in res
    assert "orthogonality" in res
    assert 0.0 <= res["splice_site_score"] <= 1.0
    assert 0.0 <= res["orthogonality"] <= 1.0


def test_run_polar_glow_smoke() -> None:
    result = run_polar_glow(params={"min_target_splice": 0.5, "max_off_target": 0.3})
    assert result.mission_id == "polar-glow-v1"
    assert result.intron.startswith("GT") or len(result.intron) > 0
    assert result.fasta.startswith(">")
    assert "primary" in result.scores
    assert 0.0 <= result.scores["primary"] <= 2.0


def test_run_forge_with_generator() -> None:
    result = run_forge(
        "polar-glow-v1",
        params={"min_target_splice": 0.6, "max_off_target": 0.25, "weight_alpha": 0.6, "weight_beta": 0.3},
        generator="preference",
        seed=42,
    )
    assert result.run_id.startswith("run_")
    assert result.ritual in ("swift", "standard", "ancient", "crystal")
    assert result.duration_ms >= 0
