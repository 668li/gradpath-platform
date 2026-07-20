"""成长模式智能 Schemas。"""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class GrowthPattern(BaseModel):
    """单个成长模式洞察。"""
    pattern_type: str  # "skill_bias" | "timeline_bias" | "confidence_calibration" | "momentum" | "domain_balance"
    title: str
    description: str
    data_points: dict  # 支撑数据
    suggestion: str


class GrowthPatternResponse(BaseModel):
    """成长模式分析结果。"""
    patterns: list[GrowthPattern]
    calibration_score: float  # 预测校准分数 0-100
    total_data_points: int
    generated_at: datetime


class CalibrationDetail(BaseModel):
    """决策预测校准详情。"""
    total_decisions: int
    reviewed_decisions: int
    avg_confidence: float
    accuracy_rate: float  # 预测准确率
    calibration_gap: float  # 置信度与准确率的差距
    insight: str
