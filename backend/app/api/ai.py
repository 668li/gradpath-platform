# backend/app/api/ai.py
"""AI 决策指导与外部数据查询 API 路由。"""
import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.exceptions import BusinessError, NotFoundError, RateLimitExceededError
from app.database import get_db
from app.main import limiter
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
from app.services.ai_circuit_breaker import AICircuitBreakerOpenError
from app.services.ai_quota_service import (
    AILLMQuotaExceeded,
    check_llm_quota,
    incr_llm_quota,
)
from app.services.ai_service import AIServiceNotConfigured, AIServiceRetryExhausted
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

# 修复: 文件内多处 logger.exception 调用未定义 logger，补全模块级 logger
logger = logging.getLogger(__name__)

router = APIRouter(tags=["AI 与外部数据"])


# ======================================================================
# AI 决策指导
# ======================================================================

@router.post(
    "/api/ai/decision-advice",
    response_model=DecisionAdviceResponse,
)
@limiter.limit("10/minute")
async def decision_advice(
    request: Request,
    response: Response,
    body: DecisionAdviceRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """AI 决策指导 — 需登录。

    降级策略：
    - LLM_API_KEY 未配置 → 503
    - LLM 超时 → 504
    - 熔断器打开 → 503
    - 配额超额 → 429
    - 其他异常 → 500
    """
    # B8: 配额检查（Redis 不可用时降级到不限制）
    try:
        await check_llm_quota(user.id)
        result = await get_decision_advice(db, user, body)
        # B8: 调用成功后递增配额计数
        await incr_llm_quota(user.id)
        return result
    except AILLMQuotaExceeded:
        raise RateLimitExceededError("今日 AI 调用次数已达上限，请明日再试")
    except AICircuitBreakerOpenError:
        raise BusinessError(
            "AI_SERVICE_UNAVAILABLE", "AI 服务暂时不可用，请稍后重试", 503,
        )
    except AIServiceRetryExhausted:
        raise BusinessError(
            "AI_TIMEOUT", "AI 服务响应超时，请稍后重试", 504,
        )
    except AIServiceNotConfigured:
        raise BusinessError(
            "AI_NOT_CONFIGURED", "AI 服务未配置（LLM_API_KEY 缺失）", 503,
        )
    except httpx.TimeoutException:
        raise BusinessError(
            "AI_TIMEOUT", "AI 分析超时，请稍后重试", 504,
        )
    except BusinessError:
        raise
    except Exception as e:
        logger.exception("AI 决策指导服务异常: %s", e)
        raise BusinessError(
            "AI_INTERNAL", "AI 决策指导服务异常，请稍后重试", 500,
        )


# ======================================================================
# AI 成长洞察
# ======================================================================

@router.post(
    "/api/ai/growth-insight",
    response_model=GrowthInsightResponse,
)
@limiter.limit("10/minute")
async def growth_insight(
    request: Request,
    response: Response,
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
    - 熔断器打开 → 503
    - 配额超额 → 429
    - 其他异常 → 500
    """
    # B8: 配额检查（Redis 不可用时降级到不限制）
    try:
        await check_llm_quota(user.id)
        result = await generate_growth_insight(db, user.id, body.period_start, body.period_end)
        # B8: 调用成功后递增配额计数（注意：growth_insight 内部可能命中缓存，
        # 此处仍然计数，避免用户通过缓存命中绕过配额）
        await incr_llm_quota(user.id)
        return result
    except AILLMQuotaExceeded:
        raise RateLimitExceededError("今日 AI 调用次数已达上限，请明日再试")
    except AICircuitBreakerOpenError:
        raise BusinessError(
            "AI_SERVICE_UNAVAILABLE", "AI 服务暂时不可用，请稍后重试", 503,
        )
    except AIServiceRetryExhausted:
        raise BusinessError(
            "AI_TIMEOUT", "AI 服务响应超时，请稍后重试", 504,
        )
    except AIServiceNotConfigured:
        raise BusinessError(
            "AI_NOT_CONFIGURED", "AI 服务未配置（LLM_API_KEY 缺失）", 503,
        )
    except httpx.TimeoutException:
        raise BusinessError(
            "AI_TIMEOUT", "AI 分析超时，请稍后重试", 504,
        )
    except BusinessError:
        raise
    except Exception as e:
        logger.exception("成长洞察服务异常: %s", e)
        raise BusinessError(
            "AI_INTERNAL", "成长洞察服务异常，请稍后重试", 500,
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
        raise NotFoundError("暂无成长洞察记录")
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


class CompanyBatchRequest(BaseModel):
    """批量获取公司元数据请求体。"""

    ids: list[str] = Field(
        ..., min_length=1, max_length=100, description="公司 ID 列表（最多 100 个）"
    )


@router.post("/api/employment/companies/batch", response_model=list[CompanyResponse])
def companies_batch(
    body: CompanyBatchRequest,
    db: Session = Depends(get_db),
):
    """批量获取公司元数据（消除前端 N+1 调用）。

    前端在作战室/就业页一次展示 N 家公司时，原需发 N 次
    `/api/companies/{id}` 请求；本接口一次返回所有公司信息。
    """
    from app.models.company import Company as CompanyModel
    from uuid import UUID as PyUUID

    # 限制单次最多 100 个，防止滥用
    raw_ids = body.ids[:100]
    parsed_ids: list[PyUUID] = []
    for raw in raw_ids:
        try:
            parsed_ids.append(PyUUID(raw))
        except (ValueError, AttributeError):
            continue
    if not parsed_ids:
        return []
    items = db.query(CompanyModel).filter(CompanyModel.id.in_(parsed_ids)).all()
    return [CompanyResponse.model_validate(c) for c in items]


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
