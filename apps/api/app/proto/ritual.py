"""锻炉 4 档难度定义(Phase 3 Task 2)。

**关键决策**:4 档是**玩家主动选择的难度**,与硬件解耦。
策略游戏的"决策密度"——更长的仪式=更高的卡牌数量=更高的潜在得分。
玩家在 Settings 主动选档位,启动时默认走最低档(急锻)。
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Ritual(str, Enum):
    """锻炉 4 档仪式枚举(字符串值,便于 JSON 序列化)。"""

    urgent = "urgent"  # 急锻
    standard = "standard"  # 主锻
    ancient = "ancient"  # 古法锻
    crystal = "crystal"  # 晶种培育


@dataclass(frozen=True)
class RitualSpec:
    """单档仪式的全部参数(不可变,便于做 cache key)。"""

    name: Ritual  # 枚举
    display_name: str  # 中文"急锻"/"主锻"/"古法锻"/"晶种培育"
    difficulty: int  # 1-4 星
    min_duration_sec: int  # 最小预期耗时(秒)
    max_duration_sec: int  # 最大预期耗时(秒,也是 asyncio timeout 上限)
    calculation_steps: int  # MCMC 步数(决定真实计算量)
    cards_complexity: int  # 玩家可见的卡牌数(急锻 4 / 主锻 6 / 古法锻 8 / 晶种培育 12)
    badge: str  # 完成后的徽章名


# 4 档常量定义(从易到极难)
URGENT_FORGE = RitualSpec(
    name=Ritual.urgent,
    display_name="急锻",
    difficulty=1,
    min_duration_sec=2,
    max_duration_sec=5,
    calculation_steps=50,
    cards_complexity=4,
    badge="急锻者",
)

STANDARD_FORGE = RitualSpec(
    name=Ritual.standard,
    display_name="主锻",
    difficulty=2,
    min_duration_sec=30,
    max_duration_sec=120,
    calculation_steps=200,
    cards_complexity=6,
    badge="主锻匠",
)

ANCIENT_FORGE = RitualSpec(
    name=Ritual.ancient,
    display_name="古法锻",
    difficulty=3,
    min_duration_sec=300,
    max_duration_sec=900,
    calculation_steps=800,
    cards_complexity=8,
    badge="古法锻师",
)

CRYSTAL_CULTIVATION = RitualSpec(
    name=Ritual.crystal,
    display_name="晶种培育",
    difficulty=4,
    min_duration_sec=1800,
    max_duration_sec=7200,
    calculation_steps=3000,
    cards_complexity=12,
    badge="晶种培育师",
)


# 查表(按枚举索引)
RITUALS: dict[Ritual, RitualSpec] = {
    Ritual.urgent: URGENT_FORGE,
    Ritual.standard: STANDARD_FORGE,
    Ritual.ancient: ANCIENT_FORGE,
    Ritual.crystal: CRYSTAL_CULTIVATION,
}


def get_ritual(name: str) -> RitualSpec:
    """字符串转 RitualSpec。

    Args:
        name: 仪式名("urgent" / "standard" / "ancient" / "crystal" 大小写均可)

    Returns:
        对应的 RitualSpec

    Raises:
        ValueError: 不认识的 ritual 名
    """
    if not isinstance(name, str):
        raise ValueError(f"ritual name must be str, got {type(name).__name__}")
    try:
        key = Ritual(name.lower())
    except ValueError as exc:
        valid = ", ".join(r.value for r in Ritual)
        raise ValueError(f"Unknown ritual: {name!r}. Valid: {valid}") from exc
    return RITUALS[key]


def default_ritual() -> RitualSpec:
    """启动默认仪式(最低档:急锻)。"""
    return URGENT_FORGE
