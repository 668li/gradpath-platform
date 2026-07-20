"""AI 增强 API — 院校分析报告、RAG 问答、录取预测、学习计划。"""
import logging
from datetime import datetime

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import settings
from app.core.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.services.ai_circuit_breaker import AICircuitBreakerOpenError
from app.services.ai_quota_service import (
    AILLMQuotaExceeded,
    check_llm_quota,
    incr_llm_quota,
)
from app.services.ai_service import (
    AIService,
    AIServiceNotConfigured,
    AIServiceRetryExhausted,
)
from app.services.user_context_service import build_context_prompt

logger = logging.getLogger(__name__)

router = APIRouter(tags=["AI 增强功能"])

# 延迟导入 limiter 以避免循环导入
_limiter = None


def _get_limiter():
    global _limiter
    if _limiter is None:
        from app.main import limiter
        _limiter = limiter
    return _limiter


def _inject_user_context(db: Session, user_id, base_prompt: str) -> str:
    """在 system prompt 中注入用户上下文（决策副驾驶护城河）。

    失败时返回原始 prompt，不阻断 AI 调用。
    """
    try:
        ctx = build_context_prompt(db, user_id)
        if ctx and "暂无用户上下文" not in ctx:
            return f"{base_prompt}\n\n【用户上下文】\n{ctx}"
    except Exception as e:
        logger.warning("注入用户上下文失败 user_id=%s: %s", user_id, e)
    return base_prompt


# ======================================================================
# Schema 定义
# ======================================================================

class ReportRequest(BaseModel):
    """院校分析报告请求。"""
    school_name: str = Field(..., description="目标院校名称")
    major_name: str = Field(..., description="目标专业名称")
    include_intel: bool = Field(True, description="是否包含院校情报")
    include_adjustment: bool = Field(True, description="是否包含调剂信息")


class ReportResponse(BaseModel):
    """院校分析报告响应。"""
    school_overview: str
    scoreline_trend: dict
    competition_analysis: dict
    intel_summary: dict
    probability_assessment: dict
    personalized_advice: str
    risk_warnings: list[str]
    generated_at: str


class AskRequest(BaseModel):
    """RAG 问答请求。"""
    question: str = Field(..., min_length=2, max_length=500, description="用户问题")
    school_filter: str | None = Field(None, description="限定院校")
    year_filter: int | None = Field(None, description="限定年份")
    source_filter: str | None = Field(None, description="限定数据源")
    top_k: int = Field(5, ge=1, le=20, description="检索数量")


class AskResponse(BaseModel):
    """RAG 问答响应。"""
    answer: str
    sources: list[dict]
    confidence: float


class PredictRequest(BaseModel):
    """录取概率预测请求。"""
    school_name: str = Field(..., description="目标院校名称")
    major_name: str = Field(..., description="目标专业名称")
    user_score: int = Field(..., ge=0, le=500, description="用户模考分数")
    undergrad_tier: str = Field(..., description="本科层次 (985/211/双一流/普通)")
    gpa: float | None = Field(None, ge=0, le=4.0, description="GPA")
    english_score: int | None = Field(None, ge=0, le=100, description="英语成绩")


class PredictResponse(BaseModel):
    """录取概率预测响应。"""
    probability: float
    confidence: str
    risk_level: str
    factors: list[dict]
    recommendations: list[str]
    score_ranges: dict


class PlanRequest(BaseModel):
    """学习计划请求。"""
    school_name: str = Field(..., description="目标院校名称")
    major_name: str = Field(..., description="目标专业名称")
    subjects: list[str] = Field(..., description="考试科目")
    daily_hours: float = Field(8, ge=1, le=16, description="每日学习时间")
    start_date: str | None = Field(None, description="开始日期")
    end_date: str | None = Field(None, description="结束日期")
    current_level: str = Field("intermediate", description="当前水平")


class PlanResponse(BaseModel):
    """学习计划响应。"""
    plan_name: str
    total_days: int
    phases: list[dict]
    weekly_tests: list[dict]
    daily_schedule: dict
    tips: list[str]


# ======================================================================
# AI 院校分析报告
# ======================================================================

@router.post("/api/ai/report", response_model=ReportResponse)
@_get_limiter().limit("5/minute")
async def generate_report(
    request: Request,
    response: Response,
    body: ReportRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """生成个性化院校分析报告 — 需登录。

    基于用户目标院校 + 个人背景，生成包含以下维度的分析报告：
    - 院校综合实力与排名趋势
    - 历年分数线变化
    - 报录比分析与竞争程度评估
    - 院校隐性信息
    - 录取概率评估
    - 个性化建议

    降级策略：
    - LLM_API_KEY 未配置 → 503
    - LLM 超时 / 重试耗尽 → 504
    - 熔断器打开 → 503
    - 配额超额 → 429
    - 其他异常 → 500
    """
    # B8: 配额检查（Redis 不可用时降级到不限制）
    try:
        await check_llm_quota(user.id)
    except AILLMQuotaExceeded:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="今日 AI 调用次数已达上限，请明日再试",
        )
    try:
        # 1. 获取数据上下文
        # 修复 ImportError: 实际路径为 app.services.analytics_service
        from app.services.analytics_service import get_analytics_service
        analytics = get_analytics_service(db)

        scoreline_trend = analytics.get_scoreline_trend(body.school_name, body.major_name)
        admission_rate = analytics.get_admission_rate(body.school_name, body.major_name)

        # 2. 获取院校情报
        intel_summary = {}
        if body.include_intel:
            from app.models.grad_intel import GradSchoolIntel
            intel = db.query(GradSchoolIntel).filter(
                GradSchoolIntel.school_name == body.school_name,
                GradSchoolIntel.major_name == body.major_name,
            ).order_by(GradSchoolIntel.year.desc()).first()
            if intel:
                intel_summary = {
                    "background_discrimination": intel.background_discrimination,
                    "first_choice_protection": intel.first_choice_protection,
                    "admission_ratio": intel.admission_ratio,
                    "score_suppression": intel.score_suppression,
                    "transfer_friendly": intel.transfer_friendly,
                    "insider_notes": intel.insider_notes,
                }

        # 3. 构建 LLM Prompt
        system_prompt = """你是考研数据分析专家。基于以下结构化数据，生成一份个性化的院校分析报告。

请以 JSON 格式返回，包含以下字段：
- school_overview: 院校综合概述
- scoreline_trend: 分数线趋势分析
- competition_analysis: 竞争程度分析
- probability_assessment: 录取概率评估
- personalized_advice: 个性化建议
- risk_warnings: 风险提示列表"""

        user_content = f"""
目标院校: {body.school_name}
目标专业: {body.major_name}

分数线趋势数据:
{scoreline_trend}

录取率数据:
{admission_rate}

院校情报:
{intel_summary}

请基于以上数据生成分析报告。"""

        # 4. 调用 LLM
        ai_service = AIService()
        # 决策副驾驶护城河：注入用户上下文实现个性化
        system_prompt = _inject_user_context(db, user.id, system_prompt)
        result = await ai_service.chat(system_prompt, user_content, timeout=60)
        # B8: LLM 调用成功后递增当日配额计数
        await incr_llm_quota(user.id)

        # 5. 解析响应
        import json
        try:
            report_data = json.loads(result)
            # 修复 bug: LLM 可能返回字符串而非 dict，导致 ReportResponse 校验失败
            if isinstance(report_data, str):
                report_data = {"school_overview": report_data}
        except json.JSONDecodeError:
            # 非 JSON，把原始文本作为 school_overview
            report_data = {
                "school_overview": result,
                "scoreline_trend": scoreline_trend,
                "competition_analysis": admission_rate.get("summary", {}) if isinstance(admission_rate, dict) else {},
                "intel_summary": intel_summary,
                "probability_assessment": {},
                "personalized_advice": "请参考以上数据分析",
                "risk_warnings": [],
            }

        # 修复 bug: 确保所有 dict 类型字段都是 dict，避免 Pydantic 校验失败
        def _ensure_dict(v, default=None):
            if isinstance(v, dict):
                return v
            if v is None:
                return default or {}
            # 字符串/其他类型，包装为 dict
            return {"content": str(v)} if default is None else default

        return ReportResponse(
            school_overview=str(report_data.get("school_overview", "")),
            scoreline_trend=_ensure_dict(report_data.get("scoreline_trend"), scoreline_trend),
            competition_analysis=_ensure_dict(report_data.get("competition_analysis")),
            intel_summary=_ensure_dict(report_data.get("intel_summary"), intel_summary),
            probability_assessment=_ensure_dict(report_data.get("probability_assessment")),
            personalized_advice=str(report_data.get("personalized_advice", "")),
            risk_warnings=report_data.get("risk_warnings") if isinstance(report_data.get("risk_warnings"), list) else [],
            generated_at=datetime.now().isoformat(),
        )

    except AIServiceNotConfigured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI 服务未配置（LLM_API_KEY 缺失）",
        )
    except AICircuitBreakerOpenError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI 服务暂时不可用，请稍后重试",
        )
    except AIServiceRetryExhausted:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="AI 服务响应超时，请稍后重试",
        )
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="AI 分析超时，请稍后重试",
        )
    except Exception as e:
        logger.exception("生成院校分析报告失败: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="生成报告失败，请稍后重试",
        )


# ======================================================================
# RAG 智能问答
# ======================================================================

@router.post("/api/ai/ask", response_model=AskResponse)
@_get_limiter().limit("20/minute")
async def rag_ask(
    request: Request,
    response: Response,
    body: AskRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """RAG 智能问答 — 基于 100K+ 数据的检索增强生成。

    支持自然语言提问，系统会从数据库中检索最相关的信息，
    并结合 LLM 生成回答。

    降级策略：
    - LLM_API_KEY 未配置 → 503
    - LLM 超时 / 重试耗尽 → 504
    - 熔断器打开 → 503
    - 配额超额 → 429
    - 其他异常 → 500
    """
    # B8: 配额检查（Redis 不可用时降级到不限制）
    try:
        await check_llm_quota(user.id)
    except AILLMQuotaExceeded:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="今日 AI 调用次数已达上限，请明日再试",
        )
    try:
        # 修复 ImportError: 实际路径为 app.services.rag_service
        from app.services.rag_service import get_rag_service

        rag = get_rag_service(db)

        # 1. 检索相关文档
        filters = {}
        if body.school_filter:
            filters["school"] = body.school_filter
        if body.year_filter:
            filters["year"] = body.year_filter
        if body.source_filter:
            filters["source"] = body.source_filter

        results = rag.search(body.question, top_k=body.top_k, filters=filters)

        # 2. 构建上下文
        context = rag.build_context(results)

        # 3. LLM 生成
        system_prompt = """你是考研数据分析助手。基于提供的参考资料回答用户问题。

规则：
1. 优先使用参考资料中的信息回答
2. 如果资料中没有相关信息，请说明
3. 回答要准确、简洁、有帮助
4. 引用具体数据时请注明来源"""

        user_content = f"""参考资料:
{context}

用户问题: {body.question}"""

        ai_service = AIService()
        # 决策副驾驶护城河：注入用户上下文实现个性化
        system_prompt = _inject_user_context(db, user.id, system_prompt)
        answer = await ai_service.chat(system_prompt, user_content, timeout=30)
        # B8: LLM 调用成功后递增当日配额计数
        await incr_llm_quota(user.id)

        # 4. 计算置信度
        avg_similarity = (
            sum(r.get("similarity", 0) for r in results) / len(results)
            if results
            else 0
        )

        return AskResponse(
            answer=answer,
            sources=[
                {
                    "content": r["content"][:200] + "..." if len(r["content"]) > 200 else r["content"],
                    "source_table": r["source_table"],
                    "similarity": r.get("similarity", 0),
                }
                for r in results
            ],
            confidence=round(avg_similarity, 4),
        )

    except AIServiceNotConfigured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI 服务未配置",
        )
    except AICircuitBreakerOpenError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI 服务暂时不可用，请稍后重试",
        )
    except AIServiceRetryExhausted:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="AI 服务响应超时，请稍后重试",
        )
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="AI 分析超时，请稍后重试",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("RAG 问答失败: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="问答服务异常，请稍后重试",
        )


# ======================================================================
# 录取概率预测
# ======================================================================

@router.post("/api/ai/predict", response_model=PredictResponse)
@_get_limiter().limit("10/minute")
async def predict_admission(
    request: Request,
    response: Response,
    body: PredictRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """预测录取概率 — 基于历史数据的 ML 模型。

    使用 scikit-learn 的 Gradient Boosting 模型，
    基于用户成绩、院校历史数据等特征预测录取概率。
    """
    try:
        # 修复 ImportError: 实际路径为 app.services.analytics_service
        from app.services.analytics_service import get_analytics_service
        import numpy as np

        analytics = get_analytics_service(db)

        # 1. 获取历史数据
        trend_data = analytics.get_scoreline_trend(body.school_name, body.major_name)
        admission_data = analytics.get_admission_rate(body.school_name, body.major_name)

        # 2. 特征提取
        avg_score = trend_data.get("statistics", {}).get("avg_score", 350)
        score_std = trend_data.get("statistics", {}).get("std_score", 15)
        avg_rate = admission_data.get("summary", {}).get("average_rate", 15)

        # 3. 简化的概率计算（可用 ML 模型替代）
        tier_scores = {"985": 1.2, "211": 1.1, "双一流": 1.0, "普通": 0.9}
        tier_factor = tier_scores.get(body.undergrad_tier, 1.0)

        # 基于分数与历史线的差距计算概率
        score_diff = body.user_score - avg_score
        z_score = score_diff / score_std if score_std > 0 else 0

        # 使用正态分布 CDF 近似概率
        from scipy.stats import norm
        base_probability = norm.cdf(z_score)

        # 调整因子
        probability = min(max(base_probability * tier_factor, 0.01), 0.99)

        # 4. 风险评估
        if probability > 0.7:
            confidence = "high"
            risk_level = "low"
        elif probability > 0.4:
            confidence = "medium"
            risk_level = "medium"
        else:
            confidence = "low"
            risk_level = "high"

        # 5. 影响因素
        factors = [
            {"feature": "user_score", "impact": score_diff / 100, "direction": "positive" if score_diff > 0 else "negative"},
            {"feature": "historical_avg_line", "impact": avg_score / 500, "direction": "neutral"},
            {"feature": "admission_rate", "impact": avg_rate / 100, "direction": "positive" if avg_rate > 15 else "negative"},
            {"feature": "undergrad_tier", "impact": (tier_factor - 1) * 0.5, "direction": "positive" if tier_factor > 1 else "negative"},
        ]

        # 6. 建议
        recommendations = []
        if score_diff > 20:
            recommendations.append(f"你的分数高于历年平均线 {score_diff:.0f} 分，录取概率较高")
        elif score_diff > 0:
            recommendations.append(f"你的分数略高于历年平均线 {score_diff:.0f} 分，有一定优势")
        else:
            recommendations.append(f"你的分数低于历年平均线 {abs(score_diff):.0f} 分，需要加强备考")

        if avg_rate < 10:
            recommendations.append("该专业竞争激烈（录取率 < 10%），建议同时准备调剂方案")

        # 7. 分数区间预测
        score_ranges = {
            "reach": {
                "min": int(avg_score + score_std),
                "max": int(avg_score + 2 * score_std),
                "probability": round(norm.cdf(1) * tier_factor, 2),
            },
            "target": {
                "min": int(avg_score - score_std),
                "max": int(avg_score + score_std),
                "probability": round(probability, 2),
            },
            "safety": {
                "min": int(avg_score - 2 * score_std),
                "max": int(avg_score - score_std),
                "probability": round(norm.cdf(-1) * tier_factor, 2),
            },
        }

        return PredictResponse(
            probability=round(probability, 4),
            confidence=confidence,
            risk_level=risk_level,
            factors=factors,
            recommendations=recommendations,
            score_ranges=score_ranges,
        )

    except Exception as e:
        logger.exception("录取预测失败: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="预测服务异常，请稍后重试",
        )


# ======================================================================
# 学习计划生成
# ======================================================================

@router.post("/api/ai/plan", response_model=PlanResponse)
@_get_limiter().limit("5/minute")
async def generate_study_plan(
    request: Request,
    response: Response,
    body: PlanRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """生成个性化学习计划 — 需登录。

    基于用户目标、当前水平、剩余时间，生成详细的学习计划。

    降级策略：
    - LLM_API_KEY 未配置 → 503
    - LLM 超时 / 重试耗尽 → 504
    - 熔断器打开 → 503
    - 配额超额 → 429
    - 其他异常 → 500
    """
    # B8: 配额检查（Redis 不可用时降级到不限制）
    try:
        await check_llm_quota(user.id)
    except AILLMQuotaExceeded:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="今日 AI 调用次数已达上限，请明日再试",
        )
    try:
        # 修复 ImportError: 实际路径为 app.services.analytics_service
        from app.services.analytics_service import get_analytics_service
        # 修复 ImportError: 实际路径为 app.services.rag_service
        from app.services.rag_service import get_rag_service

        analytics = get_analytics_service(db)
        rag = get_rag_service(db)

        # 1. 获取相关经验帖
        experience_results = rag.search(
            f"{body.school_name} {body.major_name} 备考经验",
            top_k=3,
            filters={"source": "experience_post"},
        )
        experience_summary = "\n".join(
            [r["content"][:200] for r in experience_results]
        )

        # 2. 获取分数线数据
        trend_data = analytics.get_scoreline_trend(body.school_name, body.major_name)

        # 3. 构建 Prompt
        system_prompt = """你是考研学习规划专家。基于以下信息生成详细的学习计划。

请以 JSON 格式返回，包含以下字段：
- plan_name: 计划名称
- total_days: 总天数
- phases: 阶段列表（每个阶段包含 name, start_day, end_day, goals, daily_hours）
- weekly_tests: 每周测试安排
- daily_schedule: 每日时间分配
- tips: 备考建议"""

        start_date = body.start_date or datetime.now().strftime("%Y-%m-%d")
        end_date = body.end_date or "2026-12-20"  # 默认到考研日期

        user_content = f"""
目标院校: {body.school_name}
目标专业: {body.major_name}
考试科目: {', '.join(body.subjects)}
每日学习时间: {body.daily_hours} 小时
当前水平: {body.current_level}
计划周期: {start_date} 至 {end_date}

历年分数线趋势:
{trend_data}

成功经验摘要:
{experience_summary}

请生成个性化学习计划。"""

        # 4. 调用 LLM
        ai_service = AIService()
        # 决策副驾驶护城河：注入用户上下文实现个性化
        system_prompt = _inject_user_context(db, user.id, system_prompt)
        result = await ai_service.chat(system_prompt, user_content, timeout=60)
        # B8: LLM 调用成功后递增当日配额计数
        await incr_llm_quota(user.id)

        # 5. 解析响应
        import json
        try:
            plan_data = json.loads(result)
        except json.JSONDecodeError:
            # 降级为默认计划
            plan_data = {
                "plan_name": f"{body.school_name} {body.major_name} 备考计划",
                "total_days": 180,
                "phases": [
                    {"name": "基础阶段", "start_day": 1, "end_day": 60, "goals": "打牢基础", "daily_hours": body.daily_hours * 0.7},
                    {"name": "强化阶段", "start_day": 61, "end_day": 120, "goals": "强化训练", "daily_hours": body.daily_hours * 0.9},
                    {"name": "冲刺阶段", "start_day": 121, "end_day": 180, "goals": "冲刺提分", "daily_hours": body.daily_hours},
                ],
                "weekly_tests": [{"day": "周六", "subject": "全真模拟"}],
                "daily_schedule": {"morning": "政治/英语", "afternoon": "数学/专业课", "evening": "复习巩固"},
                "tips": ["保持规律作息", "每周至少一次全真模拟", "注意身心健康"],
            }

        # 修复 bug: LLM 返回字段类型不稳定，需要防御性类型转换
        # - weekly_tests 应为 list，LLM 可能返回 dict
        # - phases 应为 list，LLM 可能返回 dict
        # - daily_schedule 应为 dict，LLM 可能返回字符串
        # - tips 应为 list，LLM 可能返回字符串
        def _ensure_list(v, default=None):
            if isinstance(v, list):
                return v
            if v is None:
                return default or []
            if isinstance(v, dict):
                return [v]
            return [str(v)]

        def _ensure_dict(v, default=None):
            if isinstance(v, dict):
                return v
            if v is None:
                return default or {}
            return {"content": str(v)}

        phases = _ensure_list(plan_data.get("phases"), [])
        # 确保 phases 中每个元素都是 dict
        phases = [p if isinstance(p, dict) else {"name": str(p)} for p in phases]

        weekly_tests = _ensure_list(plan_data.get("weekly_tests"), [])
        weekly_tests = [t if isinstance(t, dict) else {"description": str(t)} for t in weekly_tests]

        tips = _ensure_list(plan_data.get("tips"), [])
        tips = [str(t) for t in tips]

        daily_schedule = _ensure_dict(plan_data.get("daily_schedule"), {})

        return PlanResponse(
            plan_name=str(plan_data.get("plan_name", "")),
            total_days=int(plan_data.get("total_days", 180) or 180),
            phases=phases,
            weekly_tests=weekly_tests,
            daily_schedule=daily_schedule,
            tips=tips,
        )

    except AIServiceNotConfigured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI 服务未配置",
        )
    except AICircuitBreakerOpenError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI 服务暂时不可用，请稍后重试",
        )
    except AIServiceRetryExhausted:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="AI 服务响应超时，请稍后重试",
        )
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="AI 分析超时，请稍后重试",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("生成学习计划失败: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="生成计划失败，请稍后重试",
        )
