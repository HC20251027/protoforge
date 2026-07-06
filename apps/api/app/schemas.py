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
