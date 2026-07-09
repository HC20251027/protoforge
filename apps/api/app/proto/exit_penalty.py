"""退出惩罚(Phase 3 Task 3)。

**核心游戏张力**:玩家在锻造过程中退出游戏,结果根据"现实是否计算完"决定。

* 计算已经跑完 (progress >= keep_threshold) → **KEEP_RESULT**:玩家回来直接看到结果
* 计算还没跑完 (progress <  keep_threshold) → **LOSE_RESULT**:玩家回来看不到,失败

UI 顶部红色横幅固定文案:「⚠️ 锻造中退出游戏会有概率失败」。
玩家**不会看到具体百分比** — 真实决定因素是计算进度,UI 不暴露。

4 档**都**生效退出惩罚(急锻/主锻/古法锻/晶种培育),不只长任务。
原因:玩家耐心很高(可以 AFK 24 小时),惩罚核心是"你是否在游戏盯着"。
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .ritual import get_ritual


class ExitOutcome(str, Enum):
    """退出后的结果判定。"""

    KEEP_RESULT = "keep"  # 计算已经跑完 → 保留
    LOSE_RESULT = "lose"  # 计算还没跑完 → 失败/丢失


@dataclass(frozen=True)
class ExitPenaltyPolicy:
    """退出惩罚策略(不可变,便于做 cache key + 单元测试)。"""

    keep_threshold: float  # 计算进度达到这个比例就算"算完了"


# 默认策略:跑到 80% 算完成。
# 设计取舍:80% 是"几乎一定完蛋了"的临界点 — 给玩家一点点随机感(因为没看到百分比),
# 但对真的算到后期的玩家(主锻跑到 80% 应该是 100+ 秒)是个相对公平的阈值。
DEFAULT_POLICY = ExitPenaltyPolicy(keep_threshold=0.8)


# 固定 UI 文案(给玩家看的唯一字符串 — 不暴露百分比)
_UI_BANNER_TEXT = "⚠️ 锻造中退出游戏会有概率失败"


def evaluate_exit(
    current_step: int,
    total_steps: int,
    policy: ExitPenaltyPolicy = DEFAULT_POLICY,
) -> ExitOutcome:
    """根据计算进度判定退出后的结果。

    Args:
        current_step: 当前已完成的 MCMC 步数
        total_steps: 该 ritual 的 calculation_steps(总步数)
        policy: 策略(默认 80% 算完成)

    Returns:
        ExitOutcome.KEEP_RESULT / ExitOutcome.LOSE_RESULT
    """
    if total_steps <= 0:
        # 非法 total_steps → 视为"没算完" → 失败(防御性)
        return ExitOutcome.LOSE_RESULT
    if current_step < 0:
        current_step = 0
    progress = current_step / total_steps
    if progress >= policy.keep_threshold:
        return ExitOutcome.KEEP_RESULT
    return ExitOutcome.LOSE_RESULT


def evaluate_exit_from_ritual(
    current_step: int,
    ritual: str,
    policy: ExitPenaltyPolicy = DEFAULT_POLICY,
) -> ExitOutcome:
    """根据 ritual 名找 spec 的 calculation_steps 当 total,然后 evaluate。

    Args:
        current_step: 当前已完成的 MCMC 步数
        ritual: ritual 字符串("urgent"/"standard"/"ancient"/"crystal")
        policy: 策略(默认 80% 算完成)

    Returns:
        ExitOutcome.KEEP_RESULT / ExitOutcome.LOSE_RESULT
    """
    spec = get_ritual(ritual)
    return evaluate_exit(current_step, spec.calculation_steps, policy)


def _format_for_ui(outcome: ExitOutcome) -> str:
    """给玩家 UI 看的固定文案。**不**返回百分比,只返回 KEEP/LOSE 对应的固定字符串。

    设计意图:概率失败的真正决定因素是计算进度,UI 只显示提示,
    不暴露具体百分比 — 否则玩家会读出"我能从 80% 退出"这种 meta。
    """
    return _UI_BANNER_TEXT


__all__ = [
    "ExitOutcome",
    "ExitPenaltyPolicy",
    "DEFAULT_POLICY",
    "evaluate_exit",
    "evaluate_exit_from_ritual",
    "_format_for_ui",
]
