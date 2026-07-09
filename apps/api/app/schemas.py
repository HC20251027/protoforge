"""Pydantic 数据模型:API 请求/响应的契约层。"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

Ritual = Literal["urgent", "standard", "ancient", "crystal"]


# ---------------------------------------------------------------------------
# Forge
# ---------------------------------------------------------------------------

class ForgeRequest(BaseModel):
    mission_id: str = Field(..., description="任务模板 ID,如 polar-glow-v1")
    params: dict = Field(default_factory=dict, description="滑块/可调参数")
    generator: Literal["preference", "uniform", "random"] = "preference"
    seed: Optional[int] = None
    natural_language: Optional[str] = Field(
        default=None,
        description="玩家自然语言描述;若提供则服务端先翻译成 params 再 forge",
    )
    ritual: Ritual = Field(
        default="urgent",
        description="锻炉档位(玩家主动选,与硬件无关):urgent/standard/ancient/crystal",
    )


class ForgeScores(BaseModel):
    primary: float
    components: dict
    weights: dict


class ForgeResponse(BaseModel):
    run_id: str
    mission_id: str
    ritual: Ritual
    ritual_used: str = Field(
        ...,
        description="实际使用的档位枚举值(urgent/standard/ancient/crystal)",
    )
    duration_estimate_sec: int = Field(
        ...,
        description="该档位的预期耗时上限(秒),前端可据此显示进度",
    )
    duration_ms: int
    badge_unlocked: Optional[str] = Field(
        default=None,
        description="完成后授予的徽章名(急锻者/主锻匠/古法锻师/晶种培育师)",
    )
    intron: str
    fasta: str
    scores: ForgeScores
    risk_flags: list[dict] = Field(default_factory=list)
    passed_gate: bool


class RitualInfo(BaseModel):
    """某仪式对应的硬件档位信息。"""
    ritual: Ritual
    description: str
    min_gpu_mb: int
    models: list[str]


# ---------------------------------------------------------------------------
# Exit Penalty (Phase 3 Task 3)
# ---------------------------------------------------------------------------

class UnfinishedRun(BaseModel):
    """上次未完成的锻造(给前端"未完成"列表用)。"""
    run_id: str
    ritual: Ritual
    current_step: int
    total_steps: int
    started_at: str
    outcome: Literal["keep", "lose"] = Field(
        ...,
        description="退出时的判定(KEEP=算完保留,LOSE=没算完丢失)",
    )


class ExitEvaluationRequest(BaseModel):
    """手动 evaluate 某 run 的退出结果(调试/前端 resume 流程用)。"""
    run_id: str


class ExitEvaluationResponse(BaseModel):
    """evaluate 结果。"""
    outcome: Literal["keep", "lose"]
    ritual: Ritual
    progress_ratio: float = Field(
        ...,
        description="当前进度比例(0.0-1.0)。**不暴露给玩家 UI**,只给调试用。",
    )


# ---------------------------------------------------------------------------
# Shared
# ---------------------------------------------------------------------------

class ApiError(BaseModel):
    detail: str


# ---------------------------------------------------------------------------
# Missions
# ---------------------------------------------------------------------------

class SliderParam(BaseModel):
    key: str
    label: str
    min: float
    max: float
    step: float
    default: float
    description: str | None = None


class RiskRule(BaseModel):
    rule_id: str
    prompt: str
    options: list[str]
    correct: str
    explanation: str
    severity: Literal["info", "warn", "block"] = "info"


class Mission(BaseModel):
    id: str
    title: str
    description: str
    scenario: Literal["polar", "ocean", "soil", "lunar", "custom"]
    level: Literal["tutorial", "delegation", "network", "tricky", "free"]
    target_cell_line: str
    off_target: str
    intron_length_range: list[int]
    sliders: list[SliderParam] = Field(default_factory=list)
    risk_rules: list[RiskRule] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Risk Gate
# ---------------------------------------------------------------------------

class RiskCheckItem(BaseModel):
    rule_id: str
    user_answer: str
    correct: bool
    explanation: str
    severity: str


class RiskCheckRequest(BaseModel):
    mission_id: str
    answers: dict[str, str] = Field(..., description="rule_id -> 用户选项")


class RiskCheckResponse(BaseModel):
    mission_id: str
    passed: bool
    items: list[RiskCheckItem]
    score: float = Field(..., ge=0.0, le=1.0)


# ---------------------------------------------------------------------------
# Gallery
# ---------------------------------------------------------------------------

class ArtifactCreate(BaseModel):
    mission_id: str
    title: str
    intron: str
    fasta: str
    scores: dict
    ritual: str
    notes: str | None = None
    risk_passed: bool = True


class Artifact(BaseModel):
    id: str
    mission_id: str
    title: str
    intron: str
    fasta: str
    scores: dict
    ritual: str
    notes: str | None = None
    risk_passed: bool
    created_at: str


class ArtifactListResponse(BaseModel):
    items: list[Artifact]
    total: int


# ---------------------------------------------------------------------------
# Onboarding / LLM
# ---------------------------------------------------------------------------

class OnboardingStatus(BaseModel):
    active: str
    providers: list[dict]
    config: dict
    last_test_at: str | None = None
    last_test_ok: bool | None = None
    last_test_message: str = ""


class OnboardingSave(BaseModel):
    active: str
    providers: dict


class OnboardingTestRequest(BaseModel):
    name: str
    config: dict


class TranslateRequest(BaseModel):
    mission_id: str
    text: str


class TranslateResponse(BaseModel):
    mission_id: str
    values: dict
    explanation: str
    provider: str
