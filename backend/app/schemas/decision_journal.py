from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field


class DecisionJournalUpdate(BaseModel):
    """决策日志字段 — 创建/更新决策时可附加。"""
    prediction: str | None = None
    assumptions: list[str] = Field(default_factory=list)
    review_date: date | None = None


class DecisionReviewSubmit(BaseModel):
    """决策回溯评估 — 到达回溯日期后填写实际结果。"""
    actual_outcome: str
    review_notes: str | None = None
