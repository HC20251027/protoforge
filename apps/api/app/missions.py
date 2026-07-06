"""任务模板加载器(Phase 1:从 JSON 读;Phase 2:可能进 SQLite)。"""
from __future__ import annotations

import json
from pathlib import Path

from app.schemas import Mission, RiskRule, SliderParam

_TEMPLATES_DIR = Path(__file__).parent / "proto" / "templates"


def list_missions() -> list[Mission]:
    """列出所有可用任务。"""
    out: list[Mission] = []
    for path in sorted(_TEMPLATES_DIR.glob("*.json")):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        out.append(_to_mission(data))
    return out


def get_mission(mission_id: str) -> Mission:
    for m in list_missions():
        if m.id == mission_id:
            return m
    raise KeyError(mission_id)


def _extract_options(raw_options: list) -> tuple[list[str], str]:
    """把 [{value, label, correct}] 格式转成 ([label...], correct_value)。

    若 options 是字符串列表,直接返回,correct 取第一项。
    """
    if not raw_options:
        return [], ""
    if isinstance(raw_options[0], dict):
        labels = [o.get("label") or o.get("value") or "" for o in raw_options]
        correct_value = next(
            (o["value"] for o in raw_options if o.get("correct")),
            raw_options[0]["value"],
        )
        return labels, correct_value
    return list(raw_options), raw_options[0]


def _to_mission(data: dict) -> Mission:
    sliders = [
        SliderParam(
            key=s["id"] if "id" in s else s["key"],
            label=s["label"],
            min=float(s["min"]),
            max=float(s["max"]),
            step=float(s["step"]),
            default=float(s["default"]),
            description=s.get("description"),
        )
        for s in data.get("sliders", [])
    ]
    rules: list[RiskRule] = []
    for r in data.get("risk_rules", []):
        labels, correct = _extract_options(r.get("options", []))
        rules.append(
            RiskRule(
                rule_id=r["id"] if "id" in r else r["rule_id"],
                prompt=r.get("question") or r.get("prompt") or "",
                options=labels,
                correct=correct,
                explanation=r.get("explanation", ""),
                severity=r.get("severity", "info"),
            )
        )
    tpl = data["proto_template"]
    return Mission(
        id=data["task_id"],
        title=data.get("title") or data.get("name") or data["task_id"],
        description=data.get("description", ""),
        scenario=data.get("scenario", "custom"),
        level=data.get("level", "tutorial"),
        target_cell_line=tpl["target_cell_line"],
        off_target=tpl["off_target_cell_line"],
        intron_length_range=list(tpl["intron_length_range"]),
        sliders=sliders,
        risk_rules=rules,
    )
