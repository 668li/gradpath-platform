"""录取预测 API — 基于历史数据的 ML 反馈循环。"""
import logging
import math
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.grad_intel import GradScorelineRecord, GradSchoolIntel
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admission", tags=["录取预测"])

# 延迟导入 limiter 以避免循环导入
_limiter = None


def _get_limiter():
    global _limiter
    if _limiter is None:
        from app.main import limiter
        _limiter = limiter
    return _limiter


# ======================================================================
# Schema 定义
# ======================================================================

class PredictRequest(BaseModel):
    """录取概率预测请求。"""
    school_name: str = Field(..., description="目标院校名称")
    major: str = Field(..., description="目标专业名称")
    user_score: int = Field(..., ge=0, le=750, description="用户初试分数（0-750）")
    user_gpa: float = Field(..., ge=0, le=4.0, description="本科 GPA（0-4.0）")
    user_university: str = Field(..., description="本科院校名称")


class Factor(BaseModel):
    factor: str
    impact: str  # positive / negative / neutral
    weight: float


class SimilarCase(BaseModel):
    user_score: int
    outcome: str  # admitted / rejected / waitlist


class PredictResponse(BaseModel):
    """录取概率预测响应。"""
    school_name: str
    major: str
    probability: float
    confidence: str  # high / medium / low
    factors: list[Factor]
    similar_cases: list[SimilarCase]
    recommendation: str
    risk_level: str  # low / medium / high


class ScorelineHistory(BaseModel):
    year: int
    total_score_line: int | None
    enrollment_count: int | None
    application_count: int | None
    politics_score: int | None
    foreign_language_score: int | None
    business_1_score: int | None
    business_2_score: int | None


class HistoryResponse(BaseModel):
    school_name: str
    major: str
    records: list[ScorelineHistory]
    statistics: dict


# ======================================================================
# 辅助函数
# ======================================================================

def _classify_university_tier(name: str) -> str:
    """简单启发式判断院校层级。"""
    name_lower = name.lower()
    # 985 高校关键词
    tier985 = ["清华", "北大", "复旦", "上海交大", "浙江大学", "南京大学", "中国科学技术大学",
               "武汉大学", "华中科技大学", "中山大学", "哈尔滨工业大学", "西安交通大学",
               "北京航空航天", "天津大学", "南开大学", "四川大学", "吉林大学", "大连理工",
               "山东大学", "中南大学", "厦门大学", "同济大学", "华南理工", "重庆大学",
               "电子科技大学", "西北工业大学", "兰州大学", "东北大学", "湖南大学",
               "中国农业大学", "西北农林科技", "中央民族大学", "国防科技", "北京理工",
               "北京师范大学", "东南大学", "华东师范", "中国海洋"]
    # 211 关键词（含 985）
    tier211 = tier985 + ["北京邮电", "华北电力", "北京交大", "北京工业", "北京化工",
                         "北京林业", "中国政法", "中央财经", "对外经贸", "中国矿业",
                         "河海大学", "南京师范", "南京理工", "南京航天", "苏州大学",
                         "江南大学", "南京农业", "上海大学", "上海财经", "华东理工",
                         "东华大学", "上海外国语", "上海大学", "暨南大学", "华南师范",
                         "武汉理工", "华中师范", "中南财经", "西南大学", "西南财经",
                         "西南交大", "成都理工", "云南大学", "贵州大学", "广西大学",
                         "海南大学", "西藏大学", "新疆大学", "石河子大学", "宁夏大学",
                         "内蒙古大学", "延边大学", "东北师范", "东北林业", "东北农业",
                         "哈尔滨工程", "东北石油"]
    # 双一流关键词
    tier_yiliu = tier211 + ["南方科技", "上海科技", "中国科学院", "西湖大学", "深圳大学",
                           "宁波大学", "河南大学", "山西大学", "湘潭大学", "南京信息工程"]

    for t in tier985:
        if t in name:
            return "985"
    for t in tier211:
        if t in name:
            return "211"
    for t in tier_yiliu:
        if t in name:
            return "双一流"
    return "普通"


def _university_tier_weight(tier: str) -> float:
    """院校层级权重。"""
    return {"985": 1.2, "211": 1.1, "双一流": 1.0, "普通": 0.9}.get(tier, 0.9)


def _gpa_factor(gpa: float) -> float:
    """GPA 归一化因子 (0-1)。"""
    return min(gpa / 4.0, 1.0)


# ======================================================================
# 预测端点
# ======================================================================

@router.post("/predict", response_model=PredictResponse)
@_get_limiter().limit("10/minute")
def predict_admission(
    request: Request,
    response: Response,
    body: PredictRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """预测录取概率 — 基于历史数据的启发式模型。

    权重分配：
    - 分数 vs 历史平均: 40%
    - 院校层级 (985/211/双一流): 20%
    - 专业竞争比: 20%
    - GPA / 本科院校: 10%
    - 调剂友好度: 10%
    """
    try:
        # 1. 查询历史分数线
        records = (
            db.query(GradScorelineRecord)
            .filter(
                GradScorelineRecord.university_name == body.school_name,
                GradScorelineRecord.major_name == body.major,
            )
            .order_by(GradScorelineRecord.year)
            .all()
        )

        if not records:
            # 没有历史数据时，返回低置信度预测
            return PredictResponse(
                school_name=body.school_name,
                major=body.major,
                probability=0.3,
                confidence="low",
                factors=[Factor(factor="历史数据缺失", impact="negative", weight=0.4)],
                similar_cases=[],
                recommendation="该院校专业暂无历史数据，建议参考相似院校的录取情况。",
                risk_level="high",
            )

        # 2. 查询院校情报
        intel = (
            db.query(GradSchoolIntel)
            .filter(
                GradSchoolIntel.school_name == body.school_name,
                GradSchoolIntel.major_name == body.major,
            )
            .order_by(GradSchoolIntel.year.desc())
            .first()
        )

        # 3. 计算统计值
        total_scores = [r.total_score_line for r in records if r.total_score_line]
        if not total_scores:
            total_scores = [350]  # 默认

        avg_score = sum(total_scores) / len(total_scores)
        max_score = max(total_scores)
        min_score = min(total_scores)
        std_score = (sum((s - avg_score) ** 2 for s in total_scores) / len(total_scores)) ** 0.5 or 1

        # 报录比
        app_counts = [r.application_count for r in records if r.application_count]
        enroll_counts = [r.enrollment_count for r in records if r.enrollment_count]
        avg_application = sum(app_counts) / len(app_counts) if app_counts else 0
        avg_enrollment = sum(enroll_counts) / len(enroll_counts) if enroll_counts else 0
        competition_ratio = avg_application / avg_enrollment if avg_enrollment > 0 else 10

        # 4. 因子计算
        factors: list[Factor] = []

        # 4a. 分数因子 (40%)
        score_diff = body.user_score - avg_score
        z_score = score_diff / std_score
        # 使用 sigmoid 近似概率: 1 / (1 + e^(-z))
        score_prob = 1 / (1 + math.exp(-z_score))
        score_impact = "positive" if score_diff > 10 else ("negative" if score_diff < -10 else "neutral")
        factors.append(Factor(
            factor=f"分数 {body.user_score} vs 历史均分 {avg_score:.0f} (差值 {score_diff:+.0f})",
            impact=score_impact,
            weight=0.4,
        ))

        # 4b. 院校层级因子 (20%)
        tier = _classify_university_tier(body.school_name)
        tier_w = _university_tier_weight(tier)
        factors.append(Factor(
            factor=f"院校层级: {tier}",
            impact="positive" if tier_w > 1 else ("negative" if tier_w < 1 else "neutral"),
            weight=0.2,
        ))

        # 4c. 专业竞争比因子 (20%)
        comp_factor = max(0.3, 1 - competition_ratio / 50)  # 报录比越高，概率越低
        comp_impact = "positive" if competition_ratio < 8 else ("negative" if competition_ratio > 20 else "neutral")
        factors.append(Factor(
            factor=f"竞争比 {competition_ratio:.1f}:1",
            impact=comp_impact,
            weight=0.2,
        ))

        # 4d. GPA / 本科院校因子 (10%)
        gpa_w = _gpa_factor(body.user_gpa)
        undergrad_tier = _classify_university_tier(body.user_university)
        undergrad_w = _university_tier_weight(undergrad_tier)
        edu_score = (gpa_w * 0.6 + undergrad_w / 1.2 * 0.4)  # 归一化到 ~0-1
        factors.append(Factor(
            factor=f"GPA {body.user_gpa} + 本科 {undergrad_tier}",
            impact="positive" if edu_score > 0.7 else ("negative" if edu_score < 0.5 else "neutral"),
            weight=0.1,
        ))

        # 4e. 调剂友好度因子 (10%)
        transfer_w = 0.5  # 默认中立
        if intel and intel.transfer_friendly:
            transfer_map = {"yes": 0.8, "moderate": 0.5, "no": 0.2}
            transfer_w = transfer_map.get(intel.transfer_friendly, 0.5)
        factors.append(Factor(
            factor=f"调剂友好度: {intel.transfer_friendly if intel else '未知'}",
            impact="positive" if transfer_w > 0.6 else ("negative" if transfer_w < 0.4 else "neutral"),
            weight=0.1,
        ))

        # 5. 综合概率
        raw_prob = (
            score_prob * 0.4
            + tier_w / 1.2 * 0.2
            + comp_factor * 0.2
            + edu_score * 0.1
            + transfer_w * 0.1
        )
        probability = max(0.01, min(0.99, raw_prob))

        # 6. 置信度
        data_points = len(records)
        if data_points >= 5 and std_score < 20:
            confidence = "high"
        elif data_points >= 3:
            confidence = "medium"
        else:
            confidence = "low"

        # 7. 风险等级
        if probability >= 0.7:
            risk_level = "low"
        elif probability >= 0.4:
            risk_level = "medium"
        else:
            risk_level = "high"

        # 8. 相似案例 (从 outcome_reports 提取)
        similar_cases = []
        try:
            from app.models.outcome_report import OutcomeReport
            outcomes = (
                db.query(OutcomeReport)
                .filter(
                    OutcomeReport.target_school == body.school_name,
                    OutcomeReport.target_major == body.major,
                    OutcomeReport.score_total.isnot(None),
                )
                .order_by(OutcomeReport.year.desc())
                .limit(10)
                .all()
            )
            for o in outcomes:
                outcome_label = "admitted" if o.outcome_type.value == "grad_civil_career" else "rejected"
                similar_cases.append(SimilarCase(user_score=o.score_total, outcome=outcome_label))
        except Exception as e:
            logger.warning("fetch similar_cases failed: %s", e)

        # 9. 生成建议
        recommendation_parts = []
        if score_diff > 20:
            recommendation_parts.append(f"你的分数高于历年均分 {score_diff:.0f} 分，录取优势明显")
        elif score_diff > 0:
            recommendation_parts.append(f"你的分数略高于历年均分 {score_diff:.0f} 分，有一定优势")
        elif score_diff > -20:
            recommendation_parts.append(f"你的分数略低于历年均分 {abs(score_diff):.0f} 分，需加强备考")
        else:
            recommendation_parts.append(f"你的分数低于历年均分 {abs(score_diff):.0f} 分，建议考虑调剂方案")

        if competition_ratio > 15:
            recommendation_parts.append(f"该专业竞争激烈（报录比 {competition_ratio:.1f}:1），建议同时准备调剂")

        if intel and intel.background_discrimination in ("moderate", "severe"):
            recommendation_parts.append("该校存在本科歧视倾向，建议同时准备保底院校")

        recommendation = "；".join(recommendation_parts) + "。"

        return PredictResponse(
            school_name=body.school_name,
            major=body.major,
            probability=round(probability, 4),
            confidence=confidence,
            factors=factors,
            similar_cases=similar_cases,
            recommendation=recommendation,
            risk_level=risk_level,
        )
    except HTTPException:
        raise
    except Exception as e:
        # 修复: FASTAPI-RESP-001 — 不向客户端泄漏内部异常信息，仅记录日志
        logger.exception("predict_admission failed")
        raise HTTPException(status_code=500, detail="预测计算失败，请稍后重试")


# ======================================================================
# 历史数据端点
# ======================================================================

@router.get("/history/{school}/{major}", response_model=HistoryResponse)
@_get_limiter().limit("30/minute")
def get_admission_history(
    request: Request,
    response: Response,
    school: str,
    major: str,
    db: Session = Depends(get_db),
):
    """获取院校专业的历史录取数据 — 用于趋势分析。"""
    try:
        records = (
            db.query(GradScorelineRecord)
            .filter(
                GradScorelineRecord.university_name == school,
                GradScorelineRecord.major_name == major,
            )
            .order_by(GradScorelineRecord.year)
            .all()
        )

        history = [
            ScorelineHistory(
                year=r.year,
                total_score_line=r.total_score_line,
                enrollment_count=r.enrollment_count,
                application_count=r.application_count,
                politics_score=r.politics_score,
                foreign_language_score=r.foreign_language_score,
                business_1_score=r.business_1_score,
                business_2_score=r.business_2_score,
            )
            for r in records
        ]

        # 统计
        total_scores = [r.total_score_line for r in records if r.total_score_line]
        app_counts = [r.application_count for r in records if r.application_count]
        enroll_counts = [r.enrollment_count for r in records if r.enrollment_count]

        statistics = {
            "year_span": f"{records[0].year}-{records[-1].year}" if records else "",
            "data_points": len(records),
            "avg_score": round(sum(total_scores) / len(total_scores), 1) if total_scores else None,
            "max_score": max(total_scores) if total_scores else None,
            "min_score": min(total_scores) if total_scores else None,
            "avg_admission_rate": round(
                sum(e / a * 100 for e, a in zip(enroll_counts, app_counts) if a) / len(app_counts), 2
            ) if app_counts else None,
        }

        return HistoryResponse(
            school_name=school,
            major=major,
            records=history,
            statistics=statistics,
        )
    except Exception as e:
        # 修复: FASTAPI-RESP-001 — 不向客户端泄漏内部异常信息，仅记录日志
        logger.exception("get_admission_history failed")
        raise HTTPException(status_code=500, detail="查询历史数据失败，请稍后重试")
