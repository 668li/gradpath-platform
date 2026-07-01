# backend/app/schemas/assessment.py
"""职业测评 Schema 定义。"""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class QuestionOption(BaseModel):
    value: str
    label: str


class Question(BaseModel):
    id: str
    question: str
    options: list[QuestionOption]


class AssessmentSubmit(BaseModel):
    answers: dict[str, str]


class AssessmentResponse(BaseModel):
    id: UUID
    assessment_type: str
    result_code: str
    result_summary: str
    recommended_directions: list[str]
    scores: dict[str, int]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
