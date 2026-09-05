# backend/app/services/assessment_interpret_service.py
"""测评 × 专有报考数据 → 专属路径解读（护城河本体）。

把一份测评结果（霍兰德/MBTI/大五/DISC）与用户画像、真实报考数据结合，
产出「不是只给类型，而是给专属报考路径」的解读：

- 测评类型 -> 路径偏好 lean（软信号，透明规则，不编造因果）
- 用 generate_decision 拉取真实三路数据（考研/考公/就业），每条带溯源
- 用 get_prospect 拉取专业薪资前景与升学路径（真实口径，含 data_notes）
- 用 build_peer_destinations 拉取「和你分数相近的人最后去哪」的合计去向
  （参照分 = 用户自己最近一条真实回传分；从未回传分数则诚实为空）
- 每条结论都带来源；数据不足时诚实降级，绝不造假（沿用 581 溯源闸门纪律）

设计边界：
- 测评只给出「主攻方向偏好」，不越权断言「你适合哪条路」；
  落地判断交给真实数据（可报岗位数、进面线稳不稳、薪资、院校档位）。
- 所有数字均来自既有专有数据服务，本文件不引入任何硬编码薪资/分数线。
"""

from __future__ import annotations

import logging
from datetime import date
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.assessment import Assessment
from app.models.career_profile import CareerProfile
from app.models.outcome_report import OutcomeReport
from app.services.major_prospect_service import get_prospect
from app.services.path_comparison_service import build_peer_destinations
from app.services.path_decision_engine import generate_decision

logger = logging.getLogger("gradpath.assessment_interpret")

_PATH_LABELS = {
    "kaoyan": "考研",
    "civil_service": "考公",
    "employment": "就业",
}

# 霍兰德 RIASEC -> 侧重路径（数值越大越偏向；行业通识映射，透明可读）
_HOLLAND_LEAN = {
    "R": {"civil_service": 1, "employment": 3, "kaoyan": 2},  # 实际型：技术就业 + 考研深造
    "I": {"civil_service": 1, "employment": 3, "kaoyan": 4},  # 研究型：深造导向最强
    "A": {"civil_service": 1, "employment": 3, "kaoyan": 2},  # 艺术型：创意就业
    "S": {"civil_service": 4, "employment": 2, "kaoyan": 2},  # 社会型：考公/服务性机构偏好
    "E": {"civil_service": 3, "employment": 3, "kaoyan": 1},  # 企业型：就业/管理
    "C": {"civil_service": 3, "employment": 3, "kaoyan": 1},  # 常规型：稳定考公/标准就业
}

_MBTI_LEAN = {
    "INTJ": "kaoyan",
    "INTP": "kaoyan",
    "ENTJ": "employment",
    "ENTP": "employment",
    "INFJ": "civil_service",
    "INFP": "employment",
    "ENFJ": "civil_service",
    "ENFP": "employment",
    "ISTJ": "civil_service",
    "ISFJ": "civil_service",
    "ESTJ": "civil_service",
    "ESFJ": "civil_service",
    "ISTP": "employment",
    "ISFP": "employment",
    "ESTP": "employment",
    "ESFP": "employment",
}

_PROFILE_FIELDS = (
    "education_level",
    "major",
    "school_name",
    "school_tier",
    "graduation_year",
    "target_direction",
    "target_industry",
)


def _resolve_scores(scores: dict | None) -> dict:
    """规范化 scores，缺失维度假 0，避免下游 KeyError。"""
    if not scores:
        return {}
    return {str(k): (v if isinstance(v, (int, float)) else 0) for k, v in scores.items()}


def _interpret_holland(score_map: dict, code: str, major_hint: str) -> dict:
    """霍兰德 RIASEC -> 偏好 lean。code 前三位为主类型，weight 按分值归一。"""
    top3 = list(code[:3]) if code else []
    weights = {c: score_map.get(c, 0) for c in top3}
    total = sum(weights.values()) or 1
    lean_scores = dict.fromkeys(_PATH_LABELS, 0)
    for c, w in weights.items():
        for path, val in _HOLLAND_LEAN.get(c, {}).items():
            lean_scores[path] += val * (w / total)
    best = max(lean_scores, key=lean_scores.get)
    reason = f"霍兰德类型 {code or '—'}，得分最高的维度为 {', '.join(top3)}。"
    if major_hint:
        reason += f"结合专业「{major_hint}」的真实市场与报考数据，"
    reason += "生成的主攻方向偏好。方向偏好不好当作最终判断，实际可报边界见下方专有数据。"
    return {
        "primary_lean": best,
        "lean_scores": lean_scores,
        "reason": reason,
    }


def _interpret_other(assessment_type: str, code: str, major_hint: str) -> dict:
    """非霍兰德测评：给低置信度 lean，并明确标注不作为主判据。"""
    lean = _MBTI_LEAN.get(code.upper()) if assessment_type == "mbti" else None
    if lean is None:
        return {
            "primary_lean": None,
            "lean_scores": None,
            "reason": (
                "该测评主要反映性格/行为风格（非职业兴趣），"
                "不直接作为考研/考公/就业的主判据；建议结合下方真实报考数据自主决策。"
            ),
        }
    reason = (
        f"MBTI 类型 {code} 通常偏向「{_PATH_LABELS.get(lean, lean)}」。"
        + (f"结合专业「{major_hint}」的真实市场与报考数据，" if major_hint else "")
        + "这仅为通用性格倾向，落地以真实可报数据为准。"
    )
    return {
        "primary_lean": lean,
        "lean_scores": None,
        "reason": reason,
    }


def _serialize_profile(profile) -> dict | None:
    if profile is None:
        return None
    return {f: getattr(profile, f, None) for f in _PROFILE_FIELDS}


def _fresh_from_profile(profile) -> str | None:
    """应届近似判断：毕业年份不早于本年度 => 应届；否则 非应届。

    返回值与 path_decision_engine 约定的取值一致（"应届"/"非应届"）。
    空 graduate_year 则不参与过滤（返回 None）。"""
    if profile is None or profile.graduation_year is None:
        return None
    return "应届" if profile.graduation_year >= date.today().year else "非应届"


def build_interpretation(db: Session, user_id: UUID) -> dict:
    """构造测评 × 专有数据的专属路径解读。永不抛错，数据不足时诚实降级。"""
    # 1. 读取最新测评 + 用户画像
    assessment = (
        db.query(Assessment)
        .filter(Assessment.user_id == user_id)
        .order_by(Assessment.created_at.desc())
        .first()
    )
    profile = db.query(CareerProfile).filter(CareerProfile.user_id == user_id).first()

    profile_ser = _serialize_profile(profile)
    major_hint = (profile.major if profile else None) or ""
    school_tier = profile.school_tier if profile else None
    education = profile.education_level if profile else None
    graduation_year = profile.graduation_year if profile else None
    target_direction = profile.target_direction if profile else None

    # 主攻方向：优先用户自选目标方向；否则用测评 lean（软信号兜底）
    lean = target_direction or ""
    if lean and ("考公" in lean or "公" in str(lean).lower()):
        lean_path = "civil_service"
    elif lean and ("就业" in lean or "工作" in lean):
        lean_path = "employment"
    elif lean and ("考研" in lean or "升学" in lean or "深造" in lean):
        lean_path = "kaoyan"
    else:
        lean_path = None

    if assessment is not None:
        # 测评解读层（透明规则）
        score_map = _resolve_scores(assessment.scores)
        if assessment.assessment_type == "holland":
            interp = _interpret_holland(score_map, assessment.result_code or "", major_hint)
        else:
            interp = _interpret_other(
                assessment.assessment_type, assessment.result_code or "", major_hint
            )
        # 用户已明确选向时，测评 lean 降级为辅（人填的目标方向优先）
        if lean_path is not None:
            interp = dict(interp)
            interp["primary_lean"] = lean_path
            interp["reason"] = (
                f"你已在个人档案指定目标方向「{target_direction}」，覆盖测评偏好。" + interp["reason"]
            )
        assessment_block = {
            "type": assessment.assessment_type,
            "result_code": assessment.result_code,
            "scores": score_map,
            "result_summary": assessment.result_summary,
        }
        has_assessment = True
    else:
        # 倒置（2026-09-05）：测评不再是专属路径的必经入口——profile 有专业即可出路径，
        # 测评降级为可选的兴趣信号补充。无测评时如实标注，绝不伪造类型。
        score_map = {}
        interp = {
            "primary_lean": lean_path,
            "lean_scores": None,
            "reason": (
                f"你已在个人档案指定目标方向「{target_direction}」，专属路径按此生成；"
                "完成 60 秒职业测评可补齐兴趣维度，让方向偏好更稳。"
                if lean_path
                else "暂无测评信号：下方路径由你的专业与身份直接生成；"
                "完成 60 秒职业测评可让方向偏好更稳。"
            ),
        }
        assessment_block = None
        has_assessment = False

    # 2. 拉取真实三路数据（major 为空时如实标注，不生成空串聚合的假数据）
    decision = None
    if not major_hint:
        empty_reason = (
            "专业未在个人档案填写，暂时无法生成具体岗位/院校/进面线分析。"
            "请到「个人档案」补充专业后重试。"
        )
    else:
        decision = generate_decision(
            db,
            major=major_hint,
            region=None,  # 考公/就业按全国口径，不限定（无可靠省份线索）
            school_tier=school_tier,
            graduation_year=graduation_year,
            fresh_status=_fresh_from_profile(profile),
            education=education,
        )

    # 3. 同分人群去向：参照分 = 用户自己最近一条真实回传分（outcome_reports.score_total，
    #    估分是瞬时值不入库；从未回传过分数 → 诚实降级为空，不编造参照分）
    own_score_row = (
        db.query(OutcomeReport.score_total)
        .filter(
            OutcomeReport.user_id == user_id,
            OutcomeReport.score_total.isnot(None),
        )
        .order_by(OutcomeReport.created_at.desc())
        .first()
    )
    peer = build_peer_destinations(db, own_score_row[0] if own_score_row else None)

    # 4. 专业薪资前景（真实口径，含 data_notes）
    prospect = {}
    if major_hint:
        try:
            prospect = get_prospect(db, major_hint, outgoing_tier=school_tier)
        except Exception:
            logger.warning(
                "interpret: get_prospect(major=%s) 失败，降级为空", major_hint, exc_info=True
            )

    return {
        "has_assessment": has_assessment,
        "assessment": assessment_block,
        "profile": profile_ser,
        "interpretation": interp,
        "paths": decision.get("metrics", []) if decision else [],
        "recommendation": decision.get("recommendation") if decision else empty_reason,
        "input": decision.get("input") if decision else None,
        "position_analysis": decision.get("position_analysis") if decision else None,
        "school_analysis": decision.get("school_analysis") if decision else None,
        "peer_destinations": peer,
        "major_prospect": prospect,
        "data_notes": [
            "测评类型只提供方向偏好，不作为报考结论；岗位可报数/进面线/薪资/院校均来自真实专有数据。",
            "若专业/学校层次/应届尚未在个人档案填写，路径分析会放宽条件；补全后可获得更准的可报边界。",
        ],
    }
