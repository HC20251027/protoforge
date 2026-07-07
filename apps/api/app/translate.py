"""翻译:自然语言 → 滑块值。

策略:
- 当前 active provider 若是 cloud/local,调 LLM 解析(JSON 输出)。
- 失败 / disabled 模式:用关键词启发式兜底。
- 永远输出:dict[slider_key] = float,落在 [min, max] 区间。
"""
from __future__ import annotations

import json
import re
from typing import Iterable

from app.llm import load_state
from app.schemas import Mission


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _heuristic_translate(text: str, mission: Mission) -> tuple[dict, str]:
    """关键词启发式:根据自然语言里的强/弱/严/松 调整滑块。

    返回 (slider_values, explanation)。
    """
    text_l = text.lower()
    s = {p.key: p.default for p in mission.sliders}

    # 极性关键词(中英都覆盖)
    if re.search(r"严格|严苛|更紧|tight|strong|aggressive|更安全", text_l):
        if "min_target_splice" in s:
            s["min_target_splice"] = 0.85
        if "max_off_target" in s:
            s["max_off_target"] = 0.1
        if "weight_alpha" in s:
            s["weight_alpha"] = 0.7
    elif re.search(r"松|宽松|放水|loose|relax|gentle|随便", text_l):
        if "min_target_splice" in s:
            s["min_target_splice"] = 0.45
        if "max_off_target" in s:
            s["max_off_target"] = 0.35
        if "weight_alpha" in s:
            s["weight_alpha"] = 0.3

    # 步数(慢/快)
    if re.search(r"慢|多算|多跑|多搜|thorough|more steps|long", text_l):
        if "mcmc_steps" in s:
            s["mcmc_steps"] = 200
    elif re.search(r"快|少算|少跑|quick|fast|few steps|short", text_l):
        if "mcmc_steps" in s:
            s["mcmc_steps"] = 20

    # 限制到合法区间
    for p in mission.sliders:
        s[p.key] = round(_clamp(float(s[p.key]), p.min, p.max), 3)

    explanation = "启发式解析(LLM 未启用)。规则:严格→阈值↑脱靶↓;宽松→反之。"
    return s, explanation


def _llm_translate(text: str, mission: Mission) -> tuple[dict, str]:
    """用当前 LLM provider 翻译。返回 (slider_values, explanation)。"""
    from app.llm import _PROVIDERS, load_state

    state = load_state()
    if state.active == "disabled":
        raise RuntimeError("LLM disabled")
    provider = _PROVIDERS.get(state.active)
    if provider is None:
        raise RuntimeError(f"未知 provider: {state.active}")

    cfg = state.providers.get(state.active)
    schema_hint = {
        p.key: {"min": p.min, "max": p.max, "step": p.step, "default": p.default}
        for p in mission.sliders
    }
    messages = [
        {
            "role": "system",
            "content": "只输出 JSON,不要任何解释。",
        },
        {
            "role": "user",
            "content": (
                f"你是 ProtoForge 的参数翻译器。玩家给你一段自然语言描述,"
                f"你要把它转成以下滑块值(返回严格 JSON,键名不要改,值在合法区间内):\n"
                f"{json.dumps(schema_hint, ensure_ascii=False)}\n"
                f"任务背景: {mission.title}\n"
                f"任务描述: {mission.description}\n"
                f"玩家描述: {text}"
            ),
        },
    ]

    content = provider.chat(messages, temperature=0.2, max_tokens=512, config=cfg)
    match = re.search(r"\{[\s\S]*\}", content)
    if not match:
        raise RuntimeError("LLM 输出不含 JSON")
    raw = json.loads(match.group(0))

    out = {}
    for p in mission.sliders:
        v = raw.get(p.key, p.default)
        try:
            v_f = float(v)
        except (TypeError, ValueError):
            v_f = p.default
        out[p.key] = round(_clamp(v_f, p.min, p.max), 3)
    return out, f"LLM ({state.active}/{cfg.model}) 解析成功"


def translate(text: str, mission: Mission) -> tuple[dict, str]:
    """主入口:先试 LLM,失败回退到启发式。"""
    state = load_state()
    if state.active != "disabled":
        try:
            return _llm_translate(text, mission)
        except Exception as exc:  # noqa: BLE001 - 兜底
            values, _ = _heuristic_translate(text, mission)
            return values, f"LLM 失败,回退启发式: {exc}"
    return _heuristic_translate(text, mission)
