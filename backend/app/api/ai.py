# backend/app/api/ai.py
"""AI 决策指导与外部数据查询 API 路由。"""
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.ai import (
    CompanyResponse,
    DecisionAdviceRequest,
    DecisionAdviceResponse,
    GrowthInsightRequest,
    GrowthInsightResponse,
    MarketDataResponse,
    SalaryBenchmarkResponse,
)
from app.services.ai_service import AIServiceNotConfigured
from app.services.decision_advice_service import get_decision_advice
from app.services.external_data_service import (
    list_companies,
    list_market_data,
    list_salary_benchmarks,
)
from app.services.growth_insight_service import (
    generate_growth_insight,
    get_latest_insight,
)

router = APIRouter(tags=["AI 与外部数据"])


# ======================================================================
# AI 决策指导
# ======================================================================

@router.post(
    "/api/ai/decision-advice",
    response_model=DecisionAdviceResponse,
)
def decision_advice(
    body: DecisionAdviceRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """AI 决策指导 — 需登录。

    降级策略：
    - LLM_API_KEY 未配置 → 503
    - LLM 超时 → 504
    - 其他异常 → 500
    """
    try:
        return get_decision_advice(db, user, body)
    except AIServiceNotConfigured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI 服务未配置（LLM_API_KEY 缺失）",
        )
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="AI 分析超时，请稍后重试",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI 决策指导服务异常: {e}",
        )


# ======================================================================
# AI 成长洞察
# ======================================================================

@router.post(
    "/api/ai/growth-insight",
    response_model=GrowthInsightResponse,
)
def growth_insight(
    body: GrowthInsightRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """AI 成长洞察 — 需登录。

    基于用户指定时段内的职业事件、技能、决策、复盘数据生成成长分析，
    并按 event_count 缓存结果。

    降级策略：
    - LLM_API_KEY 未配置 → 503
    - LLM 超时 → 504
    - 其他异常 → 500
    """
    try:
        return generate_growth_insight(db, user.id, body.period_start, body.period_end)
    except AIServiceNotConfigured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI 服务未配置（LLM_API_KEY 缺失）",
        )
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="AI 分析超时，请稍后重试",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"成长洞察服务异常: {e}",
        )


@router.get(
    "/api/ai/growth-insight/latest",
    response_model=GrowthInsightResponse,
)
def latest_growth_insight(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取用户最近一次成长洞察（缓存）— 需登录。

    无缓存记录时返回 404。
    """
    insight = get_latest_insight(db, user.id)
    if insight is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="暂无成长洞察记录",
        )
    return insight


# ======================================================================
# 外部数据查询（公开接口）
# ======================================================================

@router.get("/api/companies", response_model=list[CompanyResponse])
def companies(
    name: str | None = Query(None, description="公司名（模糊搜索）"),
    industry: str | None = Query(None, description="行业筛选"),
    limit: int = Query(50, ge=1, le=200, description="返回数量上限"),
    db: Session = Depends(get_db),
):
    """查询公司列表（公开）。"""
    return list_companies(db, name=name, industry=industry, limit=limit)


@router.get(
    "/api/salary-benchmarks", response_model=list[SalaryBenchmarkResponse]
)
def salary_benchmarks(
    company: str | None = Query(None, description="公司筛选（模糊）"),
    position: str | None = Query(None, description="岗位筛选（模糊）"),
    city: str | None = Query(None, description="城市筛选（模糊）"),
    limit: int = Query(50, ge=1, le=200, description="返回数量上限"),
    db: Session = Depends(get_db),
):
    """查询薪资基准（公开）。"""
    return list_salary_benchmarks(
        db, company=company, position=position, city=city, limit=limit
    )


@router.get("/api/market-data", response_model=list[MarketDataResponse])
def market_data(
    category: str | None = Query(None, description="分类筛选"),
    year: int | None = Query(None, description="年份筛选"),
    industry: str | None = Query(None, description="行业筛选"),
    limit: int = Query(50, ge=1, le=200, description="返回数量上限"),
    db: Session = Depends(get_db),
):
    """查询市场宏观数据（公开）。"""
    return list_market_data(
        db, category=category, year=year, industry=industry, limit=limit
    )
