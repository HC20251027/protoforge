"""极地模板加载测试。"""
import json
from pathlib import Path


def test_polar_template_loads() -> None:
    p = Path(__file__).resolve().parents[1] / "app" / "proto" / "templates" / "polar-glow.json"
    assert p.exists()
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data["task_id"] == "polar-glow-v1"
    assert data["scenario"] == "polar"
    assert "proto_template" in data
    assert "scoring" in data["proto_template"]
    assert len(data["sliders"]) == 5
    assert len(data["risk_rules"]) >= 2
