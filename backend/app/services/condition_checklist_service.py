"""报考条件账本服务 — 从 gwy_position 行规则生成条件清单 + 用户勾选状态。

数据可行性核查结论（scripts/audit_gwy_condition_fields.py，2026-08-29）：
8 个条件字段 100% 非空；学历 9 种/政治面貌 3 种/基层年限 5 种取值，完全可枚举；
抽样 50 职位平均可生成 8.0 条结构化条件。证书类要求（四六级 425 分、计算机
等级等）藏在 remarks 自由文本，按分号切句 + 关键词规则提取。

零 LLM、纯规则，符合路线图 6 周冻结新增数据源/LLM 的约束。
"""

import re

from sqlalchemy.orm import Session

from app.models.gwy_position import GwyPosition
from app.models.user_condition_status import CONDITION_STATUSES, UserConditionStatus
from app.schemas.user_condition import (
    ConditionChecklistResponse,
    ConditionItem,
    ConditionProgress,
)

# 证书类要求的句子特征（四六级 425 分、计算机等级、资格证、普通话等）
_CERT_SENTENCE_PAT = re.compile(
    r"四六级|英语四级|英语六级|CET|计算机等级|计算机二级|三级|资格证|证书|执业资格|普通话"
)
# 无效/填充句（砍掉编号、联系方式类噪声）
_CERT_NOISE_PAT = re.compile(r"咨询电话|网址|邮箱|www\.|http")

# 要求文本为这些值时视为"对所有人无门槛"，自动计入已满足
_VACUOUS_VALUES = {"不限", "无限制", "无要求", "否", "无", "不限*"}


def _extract_cert_requirements(remarks: str | None) -> list[str]:
    """从 remarks 自由文本按分号/句号切句，提取证书类要求句子。"""
    if not remarks:
        return []
    sentences = [s.strip() for s in re.split(r"[；;。\n]", remarks) if s.strip()]
    picked: list[str] = []
    for s in sentences:
        if not _CERT_SENTENCE_PAT.search(s) or _CERT_NOISE_PAT.search(s):
            continue
        # 截断过长的复合句，保留可读性
        if len(s) > 60:
            s = s[:57] + "..."
        if s not in picked:
            picked.append(s)
    return picked[:5]


def build_conditions(position: GwyPosition) -> list[ConditionItem]:
    """规则生成条件清单：固定顺序 = 学历→学位→专业→政治→年限→经历→专业考试→证书。"""
    items: list[ConditionItem] = []

    def add(key: str, label: str, required: str | None, source: str) -> None:
        if not required or not str(required).strip():
            return
        text = str(required).strip()
        # 『不限/无限制』类要求对任何人无门槛，生成条目只是噪声，直接跳过
        if text in _VACUOUS_VALUES:
            return
        items.append(ConditionItem(key=key, label=label, required=text, source_field=source))

    add("education", "学历要求", position.education_req, "education_req")
    add("degree", "学位要求", position.degree_req, "degree_req")
    add("major", "专业要求", position.major_req, "major_req")
    add("political", "政治面貌", position.political_status, "political_status")
    add("work_years", "基层工作最低年限", position.min_work_years, "min_work_years")
    add("grassroots", "基层工作经历", position.grassroots_exp_req, "grassroots_exp_req")

    if position.professional_test == "是":
        add("professional_test", "专业科目考试", "需参加专业科目笔试", "professional_test")

    for i, cert in enumerate(_extract_cert_requirements(position.remarks)):
        add(f"cert_{i}", f"证书要求 {i + 1}", cert, "remarks")

    return items


def _is_vacuous(required: str) -> bool:
    """要求原文为『不限/无限制』类时，该条件对任何人自动视为已满足。"""
    return required in _VACUOUS_VALUES


def compute_progress(
    conditions: list[ConditionItem], statuses: dict[str, str]
) -> ConditionProgress:
    """完成度 = 已满足/总条件数；『不限』类条件自动计为已满足。"""
    met = in_progress = unmet = 0
    for c in conditions:
        if _is_vacuous(c.required):
            met += 1
            continue
        status = statuses.get(c.key, "unmet")
        if status == "met":
            met += 1
        elif status == "in_progress":
            in_progress += 1
        else:
            unmet += 1
    total = len(conditions)
    rate = round(met / total * 100, 1) if total else 0.0
    return ConditionProgress(total=total, met=met, in_progress=in_progress, unmet=unmet, rate=rate)


def get_status_map(db: Session, user_id: str, position_id: str) -> dict[str, str]:
    rows = (
        db.query(UserConditionStatus)
        .filter(
            UserConditionStatus.user_id == user_id,
            UserConditionStatus.position_id == position_id,
        )
        .all()
    )
    return {r.condition_key: r.status for r in rows}


def upsert_status(
    db: Session, user_id: str, position_id: str, condition_key: str, status: str
) -> UserConditionStatus:
    if status not in CONDITION_STATUSES:
        raise ValueError(f"非法状态: {status}")
    row = (
        db.query(UserConditionStatus)
        .filter(
            UserConditionStatus.user_id == user_id,
            UserConditionStatus.position_id == position_id,
            UserConditionStatus.condition_key == condition_key,
        )
        .first()
    )
    if row:
        row.status = status
    else:
        row = UserConditionStatus(
            user_id=user_id,
            position_id=position_id,
            condition_key=condition_key,
            status=status,
        )
        db.add(row)
    db.commit()
    db.refresh(row)
    return row


def build_checklist_response(
    db: Session, user_id: str, position: GwyPosition
) -> ConditionChecklistResponse:
    conditions = build_conditions(position)
    statuses = get_status_map(db, user_id, position.id)
    return ConditionChecklistResponse(
        position_id=position.id,
        position_code=position.position_code,
        position_name=position.position_name,
        dept_name=position.dept_name,
        year=position.year,
        conditions=conditions,
        statuses=statuses,
        progress=compute_progress(conditions, statuses),
    )
