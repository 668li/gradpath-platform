"""报考条件账本服务 — 从 gwy_position 行规则生成条件清单 + 用户勾选状态。

数据可行性核查结论（scripts/audit_gwy_condition_fields.py，2026-08-29）：
8 个条件字段 100% 非空；学历 9 种/政治面貌 3 种/基层年限 5 种取值，完全可枚举；
抽样 50 职位平均可生成 8.0 条结构化条件。证书类要求（四六级 425 分、计算机
等级等）藏在 remarks 自由文本，按分号切句 + 关键词规则提取。

零 LLM、纯规则，符合路线图 6 周冻结新增数据源/LLM 的约束。
"""

import re

from sqlalchemy.orm import Session

from app.models.grad_intel import GradScorelineRecord, GradYanzhaoProgram
from app.models.gwy_position import GwyPosition
from app.models.gwy_province_position import GwyProvincePosition
from app.models.user_condition_status import (
    CONDITION_STATUSES,
    EXAM_SOURCES,
    UserConditionStatus,
)
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


def build_province_conditions(position: GwyProvincePosition) -> list[ConditionItem]:
    """省考条件清单 — 列结构与国考不同（无政治面貌/年限列，专业分三档，
    要求集中在 other_requirements），单独一套规则。

    数据画像（scripts/audit 抽查 9344 行广东 2026）：
    grassroots_exp_req 否/是；fresh_grad_only 否/应届毕业生/2026届高校毕业生；
    other_requirements 38% 有值，多为『中共党员』类短文本。
    """
    items: list[ConditionItem] = []

    def add(key: str, label: str, required: str | None, source: str) -> None:
        if not required or not str(required).strip():
            return
        text = str(required).strip()
        if text in _VACUOUS_VALUES:
            return
        items.append(ConditionItem(key=key, label=label, required=text, source_field=source))

    add("education", "学历要求", position.education_req, "education_req")
    add("degree", "学位要求", position.degree_req, "degree_req")

    # 专业三档合并为一条（研究生：…；本科：…；大专：…），只列有值的档
    tiers: list[str] = []
    for label, col in (
        ("研究生", "major_req_grad"),
        ("本科", "major_req_undergrad"),
        ("大专", "major_req_junior"),
    ):
        val = str(getattr(position, col) or "").strip()
        if val and val not in _VACUOUS_VALUES:
            tiers.append(f"{label}：{val}")
    if tiers:
        merged = "；".join(tiers)
        if len(merged) > 120:
            merged = merged[:117] + "..."
        items.append(
            ConditionItem(
                key="major", label="专业要求", required=merged, source_field="major_req_*"
            )
        )

    if (position.grassroots_exp_req or "").strip() == "是":
        add("grassroots", "基层工作经历", "需具有基层工作经历", "grassroots_exp_req")
    if (position.psych_test or "").strip() == "是":
        add("psych_test", "心理测评", "需参加心理素质测评", "psych_test")

    fresh = (position.fresh_grad_only or "").strip()
    if fresh and fresh != "否":
        add("fresh_grad", "应届生限制", f"仅限{fresh}", "fresh_grad_only")

    add("other_req", "其他要求", position.other_requirements, "other_requirements")

    return items


def _find_kaoyan_scoreline(
    db: Session, university_name: str, major_name: str
) -> GradScorelineRecord | None:
    """按 院校+专业 取最新一年的有效复试线（total_score_line=0 为占位脏数据，须 >0）。"""
    return (
        db.query(GradScorelineRecord)
        .filter(
            GradScorelineRecord.university_name == university_name,
            GradScorelineRecord.major_name == major_name,
            GradScorelineRecord.total_score_line > 0,
        )
        .order_by(GradScorelineRecord.year.desc())
        .first()
    )


def build_kaoyan_conditions(db: Session, program: GradYanzhaoProgram) -> list[ConditionItem]:
    """考研条件清单 — 目标院校专业的复试线达标项 + 报名要求。

    数据画像（2026-08-30 审计）：分数线记录 811 条中 721 条有效（89%），
    政治/外语/业务课单科线覆盖 88%/89%/74%，年份 2022-2025；
    招研专业 150 条，admission_requirements 100% 有值。
    """
    items: list[ConditionItem] = []

    def add(key: str, label: str, required: str | None, source: str) -> None:
        if not required or not str(required).strip():
            return
        text = str(required).strip()
        if text in _VACUOUS_VALUES:
            return
        items.append(ConditionItem(key=key, label=label, required=text, source_field=source))

    line = _find_kaoyan_scoreline(db, program.university_name, program.major_name)
    if line:
        year = line.year
        add(
            "total_score",
            "复试总分线",
            f"初试 ≥{line.total_score_line} 分（{year} 复试线）",
            "total_score_line",
        )
        add("politics", "政治单科线", f"政治 ≥{line.politics_score} 分（{year}）", "politics_score")
        add(
            "foreign_language",
            "外语单科线",
            f"外语 ≥{line.foreign_language_score} 分（{year}）",
            "foreign_language_score",
        )
        add(
            "business_1",
            "业务课一单科线",
            f"业务课一 ≥{line.business_1_score} 分（{year}）",
            "business_1_score",
        )
        add(
            "business_2",
            "业务课二单科线",
            f"业务课二 ≥{line.business_2_score} 分（{year}）",
            "business_2_score",
        )

    add("admission", "报名要求", program.admission_requirements, "admission_requirements")

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


def get_status_map(
    db: Session, user_id: str, position_id: str, exam_source: str = "national"
) -> dict[str, str]:
    rows = (
        db.query(UserConditionStatus)
        .filter(
            UserConditionStatus.user_id == user_id,
            UserConditionStatus.exam_source == exam_source,
            UserConditionStatus.position_id == position_id,
        )
        .all()
    )
    return {r.condition_key: r.status for r in rows}


def upsert_status(
    db: Session,
    user_id: str,
    position_id: str,
    condition_key: str,
    status: str,
    exam_source: str = "national",
) -> UserConditionStatus:
    if status not in CONDITION_STATUSES:
        raise ValueError(f"非法状态: {status}")
    if exam_source not in EXAM_SOURCES:
        raise ValueError(f"非法赛道: {exam_source}")
    row = (
        db.query(UserConditionStatus)
        .filter(
            UserConditionStatus.user_id == user_id,
            UserConditionStatus.exam_source == exam_source,
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
            exam_source=exam_source,
            position_id=position_id,
            condition_key=condition_key,
            status=status,
        )
        db.add(row)
    db.commit()
    db.refresh(row)
    return row


def build_checklist_response(
    db: Session,
    user_id: str,
    position: GwyPosition | GwyProvincePosition | GradYanzhaoProgram,
) -> ConditionChecklistResponse:
    """国考/省考职位行 → 清单+状态+完成率。按模型类型分派规则。"""
    if isinstance(position, GradYanzhaoProgram):
        exam_source = "kaoyan"
        conditions = build_kaoyan_conditions(db, position)
    elif isinstance(position, GwyProvincePosition):
        exam_source = "province"
        conditions = build_province_conditions(position)
    else:
        exam_source = "national"
        conditions = build_conditions(position)
    statuses = get_status_map(db, user_id, position.id, exam_source)
    if isinstance(position, GradYanzhaoProgram):
        position_code = position.department
        position_name = f"{position.university_name}·{position.major_name}"
        dept_name = position.university_name
    else:
        position_code = position.position_code
        position_name = position.position_name
        dept_name = position.dept_name
    return ConditionChecklistResponse(
        position_id=position.id,
        position_code=position_code,
        position_name=position_name,
        dept_name=dept_name,
        year=position.year,
        exam_source=exam_source,
        conditions=conditions,
        statuses=statuses,
        progress=compute_progress(conditions, statuses),
    )


def get_latest_condition_summary(db: Session, user_id: str) -> dict | None:
    """用户最近核对的目标职位摘要 — 供 dashboard/AI 对话沉淀上下文。

    取最近更新的一条勾选记录定位目标职位，返回
    {exam_source, position_name, dept_name, position_code, rate, met, total}
    或 None（从未用过条件账本）。
    """
    latest = (
        db.query(UserConditionStatus)
        .filter(UserConditionStatus.user_id == user_id)
        .order_by(UserConditionStatus.updated_at.desc())
        .first()
    )
    if not latest:
        return None
    if latest.exam_source == "kaoyan":
        position = db.get(GradYanzhaoProgram, latest.position_id)
    elif latest.exam_source == "province":
        position = db.get(GwyProvincePosition, latest.position_id)
    else:
        position = db.get(GwyPosition, latest.position_id)
    if not position:
        return None
    checklist = build_checklist_response(db, user_id, position)
    return {
        "exam_source": checklist.exam_source,
        "position_name": checklist.position_name,
        "dept_name": checklist.dept_name,
        "position_code": checklist.position_code,
        "rate": checklist.progress.rate,
        "met": checklist.progress.met,
        "total": checklist.progress.total,
    }
