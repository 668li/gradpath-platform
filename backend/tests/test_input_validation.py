# backend/tests/test_input_validation.py
"""输入校验加固测试（Task 4）。"""
import pytest
from pydantic import ValidationError

from app.schemas.ai import DecisionAdviceRequest, GrowthInsightRequest
from app.schemas.employment import SearchBody
from app.schemas.retrospective import AIRetroDraftRequest


def test_decision_advice_company_too_long():
    """DecisionAdviceRequest.company 超过 100 字符 → 校验失败。"""
    with pytest.raises(ValidationError):
        DecisionAdviceRequest(destination_type="employment", company="x" * 101)


def test_decision_advice_company_max_length_ok():
    """DecisionAdviceRequest.company 恰好 100 字符 → 通过。"""
    obj = DecisionAdviceRequest(destination_type="employment", company="x" * 100)
    assert obj.company == "x" * 100


def test_growth_insight_period_end_before_start():
    """GrowthInsightRequest.period_end 早于 period_start → 校验失败。"""
    with pytest.raises(ValidationError):
        GrowthInsightRequest(period_start="2025-12-31", period_end="2025-01-01")


def test_ai_retro_draft_period_end_before_start():
    """AIRetroDraftRequest.period_end 早于 period_start → 校验失败。"""
    with pytest.raises(ValidationError):
        AIRetroDraftRequest(period_start="2025-12-31", period_end="2025-01-01")


def test_search_body_school_too_long():
    """SearchBody.school 超过 200 字符 → 校验失败。"""
    with pytest.raises(ValidationError):
        SearchBody(school="x" * 201, major="机械工程")


def test_search_body_school_max_length_ok():
    """SearchBody.school 恰好 200 字符 → 通过。"""
    obj = SearchBody(school="x" * 200, major="机械工程")
    assert obj.school == "x" * 200
