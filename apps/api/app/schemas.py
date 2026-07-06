"""Pydantic 数据模型:API 请求/响应的契约层。"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

Ritual = Literal["swift", "standard", "ancient", "crystal"]


# ---------------------------------------------------------------------------
# Forge
# ---------------------------------------------------------------------------

class ForgeRequest(BaseModel):
    mission_id: str = Field(..., description="任务模板 ID,如 polar-glow-v1")
    params: dict = Field(default_factory=dict, description="滑块/可调参数")
    generator: Literal["preference", "uniform", "random"] = "preference"
    seed: Optional[int] = None


class ForgeScores(BaseModel):
    primary: float
    components: dict
    weights: dict


class ForgeResponse(BaseModel):
    run_id: str
    mission_id: str
    ritual: Ritual
    duration_ms: int
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
