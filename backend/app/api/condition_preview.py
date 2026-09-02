"""免费可报性预览 API — 免登录「先尝一口」的转化漏斗入口。

访客无需注册：搜职位/院校 → 勾 5 个身份字段 → 立即看到可报性判定和卡在哪。
判定复用 path_decision_engine 的 blockers 实现（与登录后条件账本同一套规则、
单一实现，不产生两套口径）。考研赛道语义不同：不做资格门槛判定，
而是「估分 vs 最新复试线」给稳健/均衡/冲刺档位（复用 _classify_level）。
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.grad_intel import GradYanzhaoProgram
from app.models.gwy_position import GwyPosition
from app.models.gwy_province_position import GwyProvincePosition
from app.schemas.user_condition import ConditionPreviewRequest, ConditionPreviewResponse
from app.services.condition_checklist_service import _find_kaoyan_scoreline
from app.services.path_decision_engine import (
    _classify_level,
    _position_eligible_blockers,
    _province_position_eligible_blockers,
)

router = APIRouter(prefix="/api/condition-checklist", tags=["报考条件账本"])

# 考研单科线字段名映射：响应键 → GradScorelineRecord 列
_KAOYAN_SCORE_FIELDS = {
    "politics": "politics_score",
    "foreign_language": "foreign_language_score",
    "business_1": "business_1_score",
    "business_2": "business_2_score",
}


def _load_position(db: Session, position_ref: str, exam_source: str):
    if exam_source == "province":
        return db.get(GwyProvincePosition, position_ref)
    if exam_source == "kaoyan":
        # 兼容 hyphenated UUID 与 32-hex 两种入参（研招目录 API 返回前者）
        import uuid as _uuid

        try:
            return db.get(GradYanzhaoProgram, _uuid.UUID(position_ref))
        except (ValueError, AttributeError, TypeError):
            return None
    return db.get(GwyPosition, position_ref)


def _kaoyan_preview(
    db: Session, program: GradYanzhaoProgram, data: ConditionPreviewRequest
) -> ConditionPreviewResponse:
    """考研赛道预览：估分 vs 最新有效复试线 → 稳健/均衡/冲刺档位。"""
    base = dict(
        exam_source="kaoyan",
        position_ref=data.position_ref,
        university_name=program.university_name,
        major_name=program.major_name,
    )
    line = _find_kaoyan_scoreline(db, program.university_name, program.major_name)
    if line is None or data.kaoyan_estimated_score is None:
        if line is None:
            verdict = "该专业暂无有效复试线数据（或未公布），暂无法给出档位建议，请以院校官网为准。"
        else:
            verdict = "填写初试模考估分后，即可看到该专业的「稳健/均衡/冲刺」报考档位建议。"
        return ConditionPreviewResponse(**base, verdict_text=verdict)

    est = data.kaoyan_estimated_score
    level = _classify_level(est, float(line.total_score_line))
    score_lines = {
        key: float(getattr(line, col))
        for key, col in _KAOYAN_SCORE_FIELDS.items()
        if getattr(line, col, None) is not None
    }
    verdict = (
        f"{program.university_name} · {program.major_name} {line.year} 年复试线"
        f" {line.total_score_line} 分；你估 {est} 分，建议报考档位：{level}。"
    )
    return ConditionPreviewResponse(
        **base,
        level=level,
        total_score_line=float(line.total_score_line),
        score_lines=score_lines or None,
        verdict_text=verdict,
    )


@router.post("/preview", response_model=ConditionPreviewResponse)
def preview_eligibility(
    data: ConditionPreviewRequest,
    db: Session = Depends(get_db),
) -> ConditionPreviewResponse:
    """免费可报性判定（免登录）— 搜职位后勾身份字段，立即看能不能报、卡在哪。

    - national/province：eligible + blockers 列表 + verdict_text
    - kaoyan：level（稳健/均衡/冲刺）+ 复试线 + 单科线 + verdict_text
    """
    position = _load_position(db, data.position_ref, data.exam_source)
    if position is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "职位不存在")

    if data.exam_source == "kaoyan":
        return _kaoyan_preview(db, position, data)

    # national / province：身份快照 → blockers 判定（空=可报）。
    # 拆分「已填」与「未填」维度：未填维度可报考性无据可依，不能当作"已通过"，
    # 但也不强制填齐（转化漏斗不设门槛），用 missing_fields 显式标注，避免"缺数据当可报"。
    _IDENTITY_KEYS = (
        "fresh_status",
        "party_status",
        "education",
        "has_grassroots",
        "gender",
    )
    _MISSING_LABELS = {
        "fresh_status": "应届状态",
        "party_status": "政治面貌",
        "education": "最高学历",
        "has_grassroots": "基层工作经历",
        "gender": "性别",
    }
    conditions = {
        key: getattr(data, key) for key in _IDENTITY_KEYS if getattr(data, key, None) is not None
    }
    missing_fields = [key for key in _IDENTITY_KEYS if key not in conditions]
    if data.exam_source == "province":
        blockers = _province_position_eligible_blockers(position, conditions)
    else:
        blockers = _position_eligible_blockers(position, conditions)

    eligible = len(blockers) == 0
    if eligible:
        if missing_fields:
            missing_labels = "、".join(_MISSING_LABELS[k] for k in missing_fields)
            verdict = (
                f"已填条件满足该职位的资格门槛，但尚未填写：{missing_labels}，"
                "结论基于不完整身份，建议补全后再确认报考。"
            )
        else:
            verdict = "你的身份条件满足该职位的资格门槛，可以报考。"
    else:
        labels = "、".join(b["label"] for b in blockers)
        verdict = f"该职位暂不可报：{labels} 未满足。"
    return ConditionPreviewResponse(
        exam_source=data.exam_source,
        position_ref=data.position_ref,
        position_name=position.position_name,
        dept_name=position.dept_name,
        eligible=eligible,
        blockers=blockers,
        verdict_text=verdict,
        missing_fields=missing_fields,
        has_missing=len(missing_fields) > 0,
    )
