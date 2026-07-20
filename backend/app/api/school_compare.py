"""院校对比工具 — 多校六维雷达对比 + AI 推荐。"""
import json
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.api.school_analyst import (
    _calc_six_dimensions,
    _build_scoreline_trend,
    _fetch_dark_knowledge,
    _find_similar_schools,
    _classify_recommendation,
    _default_radar,
    DimensionScore,
    SixDimensionRadar,
    ScorelineTrendItem,
)
from app.models.grad_intel import GradSchoolIntel, GradScorelineRecord
from app.services.ai_service import AIService, AIServiceNotConfigured

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/school-compare", tags=["院校对比工具"])


# ── Schemas ──────────────────────────────────────────────────────────
class SchoolItem(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="院校名称")
    major: str = Field(..., min_length=1, max_length=100, description="专业名称")


class CompareRequest(BaseModel):
    schools: list[SchoolItem] = Field(..., min_length=2, max_length=5, description="对比院校列表（2-5所）")
    user_score: int = Field(default=360, ge=0, le=500, description="用户预估初试成绩")


class SchoolAnalysis(BaseModel):
    school_name: str
    major: str
    six_dimension_radar: SixDimensionRadar
    scoreline_trend: list[ScorelineTrendItem]
    recommendation: str  # reach / target / safe
    match_score: int = Field(..., ge=0, le=100, description="与用户分数的匹配度")


class CompareResponse(BaseModel):
    schools: list[SchoolAnalysis]
    radar_comparison: list[dict]  # 适配 SchoolRadarChart 格式
    recommendation_summary: dict  # {reach: [...], target: [...], safe: [...]}
    ai_summary: str


# ── Helpers ──────────────────────────────────────────────────────────
def _analyze_school(db: Session, name: str, major: str, user_score: int) -> dict:
    """分析单个院校，返回分析结果。"""
    intel = (
        db.query(GradSchoolIntel)
        .filter(
            GradSchoolIntel.school_name.ilike(f"%{name}%"),
            GradSchoolIntel.major_name.ilike(f"%{major}%"),
        )
        .first()
    )
    scoreline = (
        db.query(GradScorelineRecord)
        .filter(
            GradScorelineRecord.university_name.ilike(f"%{name}%"),
            GradScorelineRecord.major_name.ilike(f"%{major}%"),
        )
        .order_by(GradScorelineRecord.year.desc())
        .first()
    )

    radar = _calc_six_dimensions(intel, scoreline)
    trend = _build_scoreline_trend(db, name, major)
    recommendation = _classify_recommendation(scoreline, user_score)

    # 匹配度计算：基于用户分数与分数线的差距
    match_score = 50
    if scoreline and scoreline.total_score_line:
        diff = user_score - scoreline.total_score_line
        if diff >= 30:
            match_score = 90
        elif diff >= 10:
            match_score = 75
        elif diff >= 0:
            match_score = 60
        elif diff >= -20:
            match_score = 40
        else:
            match_score = 20

    return {
        "school_name": name,
        "major": major,
        "six_dimension_radar": radar,
        "scoreline_trend": trend,
        "recommendation": recommendation,
        "match_score": match_score,
    }


def _build_radar_comparison(analyses: list[dict]) -> list[dict]:
    """构建适配 SchoolRadarChart 的雷达对比数据。"""
    dim_labels = {
        "admission_difficulty": "录取难度",
        "first_choice_protection": "一志愿保护",
        "transfer_friendliness": "调剂友好度",
        "score_suppression_risk": "压分风险",
        "info_transparency": "信息透明",
        "cost_effectiveness": "性价比",
    }
    result = []
    for a in analyses:
        scores = {}
        for k, label in dim_labels.items():
            scores[label] = a["six_dimension_radar"][k]["score"]
        result.append({"name": a["school_name"], "scores": scores})
    return result


async def _generate_comparison_summary(analyses: list[dict], user_score: int) -> str:
    """用 AI 生成对比总结。"""
    try:
        ai = AIService()
        system_prompt = (
            "你是一位资深考研规划师。请基于以下多校对比数据，生成一段200字左右的对比分析和择校建议。"
            "要求：客观对比各校优劣，给出明确推荐。不要使用 emoji。"
        )
        schools_info = []
        for a in analyses:
            schools_info.append(
                f"{a['school_name']}{a['major']}："
                f"录取难度{a['six_dimension_radar']['admission_difficulty']['score']}，"
                f"一志愿保护{a['six_dimension_radar']['first_choice_protection']['score']}，"
                f"匹配度{a['match_score']}分，分类={a['recommendation']}"
            )
        user_content = (
            f"用户预估初试成绩：{user_score}\n"
            f"对比院校：\n" + "\n".join(schools_info)
        )
        return await ai.chat(system_prompt, user_content, timeout=30)
    except (AIServiceNotConfigured, Exception) as e:
        logger.warning("AI 对比总结生成失败: %s", e)
        reaches = [a["school_name"] for a in analyses if a["recommendation"] == "reach"]
        targets = [a["school_name"] for a in analyses if a["recommendation"] == "target"]
        safes = [a["school_name"] for a in analyses if a["recommendation"] == "safe"]
        parts = []
        if reaches:
            parts.append(f"冲刺院校：{', '.join(reaches)}")
        if targets:
            parts.append(f"稳妥院校：{', '.join(targets)}")
        if safes:
            parts.append(f"保底院校：{', '.join(safes)}")
        return "；".join(parts) + "。建议根据个人实际情况综合选择。"


# ── Endpoint ─────────────────────────────────────────────────────────
@router.post("/compare", response_model=CompareResponse, summary="多校对比分析")
async def compare_schools(
    req: CompareRequest,
    db: Session = Depends(get_db),
):
    """对比 2-5 所院校，返回六维雷达对比矩阵 + 冲/稳/保分类 + AI 建议。"""
    try:
        analyses = []
        for item in req.schools:
            a = _analyze_school(db, item.name.strip(), item.major.strip(), req.user_score)
            analyses.append(a)

        radar_comparison = _build_radar_comparison(analyses)

        # 按推荐分类汇总
        recommendation_summary = {"reach": [], "target": [], "safe": []}
        for a in analyses:
            recommendation_summary[a["recommendation"]].append(a["school_name"])

        # AI 总结
        ai_summary = await _generate_comparison_summary(analyses, req.user_score)
    except Exception as e:
        # 修复: FASTAPI-RESP-001 — 不向客户端泄漏内部异常信息，仅记录日志
        logger.exception("School comparison error: %s", e)
        raise HTTPException(status_code=500, detail="院校对比失败，请稍后重试")

    return CompareResponse(
        schools=[SchoolAnalysis(**a) for a in analyses],
        radar_comparison=radar_comparison,
        recommendation_summary=recommendation_summary,
        ai_summary=ai_summary,
    )
