"""决策分析 Schemas。"""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class Criterion(BaseModel):
    criterion: str
    weight: int = Field(..., ge=1, le=100)


class MatrixOption(BaseModel):
    name: str
    scores: dict  # {criterion_name: score(1-10)}


class PremortemReason(BaseModel):
    reason: str
    category: str = ""


class Safeguard(BaseModel):
    category: str
    action: str


class RedTeamQABase(BaseModel):
    question: str
    answer: str = ""


class DecisionAnalysisCreate(BaseModel):
    title: str = Field(..., max_length=200)
    decision_id: UUID | None = None
    options: list[str] = Field(default_factory=list)
    premortem_reasons: list[PremortemReason] = Field(default_factory=list)
    premortem_categories: list[str] = Field(default_factory=list)
    safeguards: list[Safeguard] = Field(default_factory=list)
    criteria: list[Criterion] = Field(default_factory=list)
    matrix_scores: list[dict] = Field(default_factory=list)
    red_team_questions: list[str] = Field(default_factory=list)
    red_team_answers: list[str] = Field(default_factory=list)


class DecisionAnalysisResponse(BaseModel):
    id: UUID
    decision_id: UUID | None
    title: str
    options: list
    premortem_reasons: list
    premortem_categories: list
    safeguards: list
    criteria: list
    matrix_scores: list
    weighted_results: list
    winner: str | None
    red_team_questions: list
    red_team_answers: list
    ai_analysis: str | None
    recommendation: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class MatrixComputeRequest(BaseModel):
    """计算决策矩阵加权得分。"""
    criteria: list[Criterion]
    matrix_scores: list[MatrixOption]


class PremortemAnalyzeRequest(BaseModel):
    """AI 分析预验尸结果。"""
    title: str
    options: list[str]
    premortem_reasons: list[str]


class RedTeamGenerateRequest(BaseModel):
    """AI 生成红队质疑问题。"""
    title: str
    options: list[str]
    reasoning: str | None = None
