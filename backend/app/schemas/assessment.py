# backend/app/schemas/assessment.py
"""职业测评 Schema 定义。"""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class QuestionOption(BaseModel):
    value: str
    label: str


class Question(BaseModel):
    """测评题目。

    通过 options 列表统一兼容三种题目形式：
    - 2 选项（霍兰德 / MBTI）：options 长度为 2
    - 4 选项（DISC）：options 长度为 4，分别对应 D/I/S/C
    - 5 级 Likert（大五人格）：options 长度为 5，value 为 "1"~"5"
    """

    id: str
    question: str
    options: list[QuestionOption]


class AssessmentSubmit(BaseModel):
    """提交测评答案。

    answers 形如 {"q1": "R", ...} 或 {"mbti_q1": "E", ...} 或
    {"bf_q1": "4", ...} 或 {"disc_q1": "D", ...}。
    assessment_type 默认 "holland" 以保持向后兼容。
    支持取值："holland" | "mbti" | "big_five" | "disc"。
    """

    answers: dict[str, str]
    assessment_type: str = "holland"


class AssessmentResponse(BaseModel):
    id: UUID
    assessment_type: str
    result_code: str
    result_summary: str
    recommended_directions: list[str]
    scores: dict[str, int]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
