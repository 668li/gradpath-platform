"""AI 院校分析师 — 六维雷达 + 分数线趋势 + 暗知识洞察 + 择校分类。"""
import json
import logging
import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.grad_intel import (
    DarkKnowledge,
    GradSchoolIntel,
    GradScorelineRecord,
)
from app.services.ai_service import AIService, AIServiceNotConfigured

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/school-analyst", tags=["AI院校分析师"])


# ── Schemas ──────────────────────────────────────────────────────────
class AnalystReportRequest(BaseModel):
    school_name: str = Field(..., min_length=1, max_length=100, description="院校名称", examples=["清华大学"])
    major: str = Field(..., min_length=1, max_length=100, description="专业名称", examples=["计算机科学与技术"])


class DimensionScore(BaseModel):
    score: int = Field(..., ge=1, le=10)
    description: str


class SixDimensionRadar(BaseModel):
    admission_difficulty: DimensionScore
    first_choice_protection: DimensionScore
    transfer_friendliness: DimensionScore
    score_suppression_risk: DimensionScore
    info_transparency: DimensionScore
    cost_effectiveness: DimensionScore


class ScorelineTrendItem(BaseModel):
    year: int
    score_line: int | None = None
    competition_ratio: str | None = None


class AnalystReportResponse(BaseModel):
    school_name: str
    major: str
    six_dimension_radar: SixDimensionRadar
    scoreline_trend: list[ScorelineTrendItem]
    dark_knowledge_highlights: list[str]
    similar_schools: list[str]
    recommendation: str  # reach / target / safe
    summary: str


# ── Helpers ──────────────────────────────────────────────────────────
_LEVEL_MAP = {"985": 10, "211": 7, "双一流": 6, "一本": 5, "二本": 3, "三本": 2}
_PROTECT_MAP = {"yes": 9, "partial": 6, "no": 2, "unknown": 5}
_SUPPRESS_MAP = {"none": 9, "light": 7, "moderate": 4, "severe": 2, "unknown": 5}
_TRANSFER_MAP = {"yes": 9, "moderate": 6, "no": 2, "unknown": 5}


def _calc_six_dimensions(intel: GradSchoolIntel | None, scoreline: GradScorelineRecord | None) -> dict:
    """从结构化字段计算六维得分。"""
    if not intel:
        return _default_radar()

    # 1) 录取难度 — 基于院校层次 + 报录比
    diff = _LEVEL_MAP.get(intel.school_tier, 5)
    if intel.admission_ratio:
        try:
            parts = str(intel.admission_ratio).split(":")
            ratio = float(parts[0]) / float(parts[1]) if len(parts) == 2 else 0
            if ratio > 30:
                diff = min(10, diff + 3)
            elif ratio > 15:
                diff = min(10, diff + 1)
            elif ratio < 5:
                diff = max(1, diff - 2)
        except (ValueError, IndexError, ZeroDivisionError) as e:
            logger.warning("parse admission_ratio failed (%s): %s", intel.admission_ratio, e)
    diff = max(1, min(10, diff))

    # 2) 一志愿保护
    prot = _PROTECT_MAP.get(intel.first_choice_protection, 5)

    # 3) 调剂友好度
    trans = _TRANSFER_MAP.get(intel.transfer_friendly, 5)

    # 4) 压分风险
    supp = _SUPPRESS_MAP.get(intel.score_suppression, 5)

    # 5) 信息透明度 — 有数据来源 + 标签越多越透明
    sources = intel.data_sources if isinstance(intel.data_sources, list) else []
    tags = intel.tags if isinstance(intel.tags, list) else []
    info = 5
    if len(sources) >= 3:
        info += 2
    elif len(sources) >= 1:
        info += 1
    if intel.insider_notes:
        info += 1
    if intel.retest_format:
        info += 1
    info = min(10, info)

    # 6) 性价比 — 985 基础分 + 名额/竞争比
    cost = 6
    if intel.school_tier in ("985", "211"):
        cost += 2
    if intel.actual_quota and intel.actual_quota > 20:
        cost += 1
    if scoreline and scoreline.enrollment_count and scoreline.application_count:
        ratio = scoreline.application_count / max(scoreline.enrollment_count, 1)
        if ratio < 10:
            cost += 1
        elif ratio > 30:
            cost -= 1
    cost = max(1, min(10, cost))

    descriptions = {
        "admission_difficulty": "录取难度",
        "first_choice_protection": "一志愿保护",
        "transfer_friendliness": "调剂友好度",
        "score_suppression_risk": "压分风险（越高越公平）",
        "info_transparency": "信息透明度",
        "cost_effectiveness": "性价比",
    }

    raw = [diff, prot, trans, supp, info, cost]
    keys = list(descriptions.keys())

    # Ensure all scores are within 1-10
    raw = [max(1, min(10, s)) for s in raw]

    return {
        k: {"score": s, "description": f"{descriptions[k]}：{'低' if s <= 3 else '中' if s <= 6 else '高'}（{s}/10）"}
        for k, s in zip(keys, raw)
    }


def _default_radar() -> dict:
    keys = [
        ("admission_difficulty", "录取难度"),
        ("first_choice_protection", "一志愿保护"),
        ("transfer_friendliness", "调剂友好度"),
        ("score_suppression_risk", "压分风险（越高越公平）"),
        ("info_transparency", "信息透明度"),
        ("cost_effectiveness", "性价比"),
    ]
    return {k: {"score": 5, "description": f"{d}：数据不足（5/10）"} for k, d in keys}


def _build_scoreline_trend(db: Session, school: str, major: str) -> list[dict]:
    records = (
        db.query(GradScorelineRecord)
        .filter(
            GradScorelineRecord.university_name.ilike(f"%{school}%"),
            GradScorelineRecord.major_name.ilike(f"%{major}%"),
        )
        .order_by(GradScorelineRecord.year)
        .all()
    )
    trend = []
    for r in records:
        ratio = None
        if r.application_count and r.enrollment_count and r.enrollment_count > 0:
            ratio = f"{r.application_count / r.enrollment_count:.1f}:1"
        trend.append({
            "year": r.year,
            "score_line": r.total_score_line,
            "competition_ratio": ratio,
        })
    return trend


def _fetch_dark_knowledge(db: Session, school: str, major: str) -> list[str]:
    """从 dark_knowledge 表 + grad_school_intel.insider_notes 组合暗知识。"""
    highlights: list[str] = []

    # 1) 院校情报中的 insider_notes
    intel = (
        db.query(GradSchoolIntel)
        .filter(
            GradSchoolIntel.school_name.ilike(f"%{school}%"),
            GradSchoolIntel.major_name.ilike(f"%{major}%"),
        )
        .first()
    )
    if intel and intel.insider_notes:
        highlights.append(intel.insider_notes[:200])

    # 2) 暗知识表中择校相关条目
    dk_items = (
        db.query(DarkKnowledge)
        .filter(DarkKnowledge.stage.in_(["school_selection", "retest"]))
        .order_by(DarkKnowledge.importance.desc(), DarkKnowledge.sort_order)
        .limit(10)
        .all()
    )
    for dk in dk_items[:5]:
        highlights.append(f"【{dk.title}】{dk.content[:120]}...")

    return highlights[:5]


def _classify_recommendation(scoreline: GradScorelineRecord | None, user_score: int | None = 360) -> str:
    """根据分数线对用户成绩进行冲/稳/保分类。"""
    if not scoreline or not scoreline.total_score_line:
        return "target"
    line = scoreline.total_score_line
    if user_score and user_score < line:
        return "reach"
    elif user_score and user_score >= line + 20:
        return "safe"
    return "target"


async def _generate_summary(
    school: str,
    major: str,
    radar: dict,
    trend: list,
    dark_knowledge: list,
    similar: list,
) -> str:
    """用 AI 生成 200 字总结。"""
    try:
        ai = AIService()
        system_prompt = (
            "你是一位资深考研规划师，请基于以下数据为院校生成一段200字左右的分析总结。"
            "要求：客观、实用、有洞察力。不要使用 emoji。"
        )
        user_content = (
            f"院校：{school}，专业：{major}\n"
            f"六维评分：{json.dumps(radar, ensure_ascii=False)}\n"
            f"历年分数线：{json.dumps(trend[-3:], ensure_ascii=False)}\n"
            f"关键洞察：{json.dumps(dark_knowledge[:3], ensure_ascii=False)}\n"
            f"相似院校：{', '.join(similar)}"
        )
        return await ai.chat(system_prompt, user_content, timeout=30)
    except (AIServiceNotConfigured, Exception) as e:
        logger.warning("AI 总结生成失败，使用降级文案: %s", e)
        return (
            f"{school}{major}专业综合分析：根据现有数据，"
            f"该校在录取难度、信息透明度等方面表现{'较好' if radar.get('info_transparency', {}).get('score', 5) > 6 else '一般'}。"
            f"建议考生结合历年分数线趋势和个人成绩进行综合判断。"
        )


def _find_similar_schools(db: Session, school: str, major: str) -> list[str]:
    """查找相似院校（同层次 + 同专业方向）。"""
    intel = (
        db.query(GradSchoolIntel)
        .filter(
            GradSchoolIntel.school_name.ilike(f"%{school}%"),
            GradSchoolIntel.major_name.ilike(f"%{major}%"),
        )
        .first()
    )
    tier = intel.school_tier if intel else ""
    if not tier:
        return []

    others = (
        db.query(GradSchoolIntel.school_name)
        .filter(
            GradSchoolIntel.school_tier == tier,
            GradSchoolIntel.major_name.ilike(f"%{major}%"),
            GradSchoolIntel.school_name != school,
        )
        .distinct()
        .limit(5)
        .all()
    )
    return [o[0] for o in others]


# ── Endpoint ─────────────────────────────────────────────────────────
@router.post("/report", response_model=AnalystReportResponse, summary="AI 院校分析报告")
async def generate_report(
    req: AnalystReportRequest,
    db: Session = Depends(get_db),
):
    """生成院校六维雷达 + 趋势 + 暗知识 + 推荐分类的一站式分析报告。"""
    school = req.school_name.strip()
    major = req.major.strip()

    # 1) 查询院校情报
    intel = (
        db.query(GradSchoolIntel)
        .filter(
            GradSchoolIntel.school_name.ilike(f"%{school}%"),
            GradSchoolIntel.major_name.ilike(f"%{major}%"),
        )
        .first()
    )

    # 2) 查询最新分数线
    scoreline = (
        db.query(GradScorelineRecord)
        .filter(
            GradScorelineRecord.university_name.ilike(f"%{school}%"),
            GradScorelineRecord.major_name.ilike(f"%{major}%"),
        )
        .order_by(GradScorelineRecord.year.desc())
        .first()
    )

    # 3) 计算六维雷达
    radar = _calc_six_dimensions(intel, scoreline)

    # 4) 分数线趋势
    trend = _build_scoreline_trend(db, school, major)

    # 5) 暗知识
    dark_knowledge = _fetch_dark_knowledge(db, school, major)

    # 6) 相似院校
    similar = _find_similar_schools(db, school, major)

    # 7) 冲/稳/保分类
    recommendation = _classify_recommendation(scoreline)

    # 8) AI 总结
    summary = await _generate_summary(school, major, radar, trend, dark_knowledge, similar)

    return AnalystReportResponse(
        school_name=school,
        major=major,
        six_dimension_radar=SixDimensionRadar(**radar),
        scoreline_trend=[ScorelineTrendItem(**t) for t in trend],
        dark_knowledge_highlights=dark_knowledge,
        similar_schools=similar,
        recommendation=recommendation,
        summary=summary,
    )
