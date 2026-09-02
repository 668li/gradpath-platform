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
from app.models.user_condition_status import CONDITION_STATUSES, EXAM_SOURCES, UserConditionStatus
from app.schemas.user_condition import ConditionChecklistResponse, ConditionItem, ConditionProgress
from app.services.grad_intel_service import scoreline_has_traceable_source

# 证书类要求的句子特征（四六级 425 分、计算机等级、资格证、普通话等）
_CERT_SENTENCE_PAT = re.compile(
    r"四六级|英语四级|英语六级|CET|计算机等级|计算机二级|三级|资格证|证书|执业资格|普通话"
)
# 无效/填充句（砍掉编号、联系方式类噪声）
_CERT_NOISE_PAT = re.compile(r"咨询电话|网址|邮箱|www\.|http")

# 要求文本为这些值时视为"对所有人无门槛"，自动计入已满足
_VACUOUS_VALUES = {"不限", "无限制", "无要求", "否", "无", "不限*"}

# 条件类型分类（保守规则，宁可不武断不可误判）
# 硬门槛特征词：出现在要求文本中即视为"决定能不能报"的资格锁
_HARD_GATE_MARKERS = ("仅限", "限", "必须", "中共党员", "应届毕业生", "面向应届")
# 明确开放/可补的信号：与硬门槛同现或单独出现时，倾向不判定为硬门槛
_OPEN_MARKERS = ("及以上", "或以上", "或", "不限", "可", "优先", "具有", "取得")
# 有效性上决定"能否报名"的条件键（配合文本措辞决定是否标 hard_gate）
_HARD_GATE_KEYS = {
    "education",
    "degree",
    "political",
    "work_years",
    "grassroots",
    "fresh_grad",
    "major",
}


def _classify_condition(key: str, required: str) -> str:
    """按条件键 + 措辞给一条条件标类型。

    hard_gate：资格锁死项。仅当文本含闭锁词（仅限/必须/中共党员/应届毕业生）且
    不含开放词（及以上/或/不限）时判定；否则宁可不判定。分数/证书/考试类键（分数、
    证书、专业考试、心理测评）一律视为 actionable（可补项）。
    """
    text = str(required or "").strip()
    if not text:
        return "unclassified"
    # 可补项键：分数/证书/考试，努力可得，不锁资格
    if (
        key in ("total_score", "politics", "foreign_language", "business_1", "business_2")
        or key in ("professional_test", "psych_test")
        or key.startswith("cert_")
    ):
        return "actionable"
    if key in _HARD_GATE_KEYS and any(m in text for m in _HARD_GATE_MARKERS):
        # 同一文本若含开放表述（"及以上/或/不限"），说明仍有回旋余地，不武断
        if not any(om in text for om in _OPEN_MARKERS):
            return "hard_gate"
    return "unclassified"


def _action_hint(key: str, category: str, required: str) -> str | None:
    """给一条『未满足』条件生成行动建议文本（纯规则，零 LLM）。"""
    if category == "hard_gate":
        return (
            "这条是资格硬门槛：不满足基本无法报考此职位/专业。建议核对是否有同级替代岗，"
            "或改报不限制此项的方向——已满足其余条件也救不回这一条。"
        )
    if category == "actionable":
        # 可补项：按条件键给具体补法
        if key in ("total_score", "politics", "foreign_language", "business_1", "business_2"):
            return "这是分数门槛，靠备考提高初试/模考分可达标。对照目标分数拆复习计划。"
        if key == "cert_":
            return "这是证件要求：可在报考窗口前考取（如四六级/计算机等级/资格证）。查清报名时间与周期，列入行动清单。"
        if key == "professional_test":
            return "这是加考科目：笔试阶段需额外准备，属可补项。列入复习计划即可。"
        if key == "psych_test":
            return "这是入职流程环节（心理测评），非资格门槛，达标即可，无需提前备考。"
        return "这条可通过持续努力获得满足（能力/材料准备类），列入长期行动项即可。"
    return None


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
        items.append(
            ConditionItem(
                key=key,
                label=label,
                required=text,
                source_field=source,
                category=_classify_condition(key, text),
            )
        )

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
        items.append(
            ConditionItem(
                key=key,
                label=label,
                required=text,
                source_field=source,
                category=_classify_condition(key, text),
            )
        )

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
    records = (
        db.query(GradScorelineRecord)
        .filter(
            GradScorelineRecord.university_name == university_name,
            GradScorelineRecord.major_name == major_name,
            GradScorelineRecord.total_score_line > 0,
        )
        .order_by(GradScorelineRecord.year.desc())
        .all()
    )
    # 溯源过滤：无具体溯源（URL/数据文件）的记录不作可报性判定依据
    records = [r for r in records if scoreline_has_traceable_source(r.data_sources)]
    return records[0] if records else None


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
        items.append(
            ConditionItem(
                key=key,
                label=label,
                required=text,
                source_field=source,
                category=_classify_condition(key, text),
            )
        )

    line = _find_kaoyan_scoreline(db, program.university_name, program.major_name)
    if line:
        year = line.year
        add(
            "total_score",
            "复试总分线",
            f"初试 ≥{line.total_score_line} 分（{year} 复试线）",
            "total_score_line",
        )
        # 单科线可能为 None（业务课二覆盖率仅 74%），为空不生成该条
        if line.politics_score:
            add(
                "politics",
                "政治单科线",
                f"政治 ≥{line.politics_score} 分（{year}）",
                "politics_score",
            )
        if line.foreign_language_score:
            add(
                "foreign_language",
                "外语单科线",
                f"外语 ≥{line.foreign_language_score} 分（{year}）",
                "foreign_language_score",
            )
        if line.business_1_score:
            add(
                "business_1",
                "业务课一单科线",
                f"业务课一 ≥{line.business_1_score} 分（{year}）",
                "business_1_score",
            )
        if line.business_2_score:
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
    # 考研专业表主键是原生 UUID（hyphenated 36 字符），统一转 32-hex 存取
    if isinstance(position, GradYanzhaoProgram):
        position_ref = position.id.hex
    else:
        position_ref = position.id
    statuses = get_status_map(db, user_id, position_ref, exam_source)
    if isinstance(position, GradYanzhaoProgram):
        position_code = position.department
        position_name = f"{position.university_name}·{position.major_name}"
        dept_name = position.university_name
        response_position_id = position_ref
    else:
        position_code = position.position_code
        position_name = position.position_name
        dept_name = position.dept_name
        response_position_id = position.id
    return ConditionChecklistResponse(
        position_id=response_position_id,
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
        import uuid as _uuid

        position = db.get(GradYanzhaoProgram, _uuid.UUID(latest.position_id))
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


# 从条件账本可诚实推导的「决策引擎身份包」字段（其余字段不猜，留人工填）
# 文本里出现这些教育层次词即视为证据（要求写的必须是用户已满足的那档）
_EDU_HINT_WORDS = {
    "博士": "博士",
    "硕士": "硕士",
    "研究生": "硕士",
    "本科": "本科",
    "大专": "大专",
}


def _importable_package(checklist) -> dict:
    """从最近核对的职位条件 + 勾选状态，推导可安全导入决策引擎的身份字段。

    只导出能由「已满足」直接证明、且不会误导可报边界过滤的二元事实：
    - fresh_status：应届生限制条件已满足 → 应届；已确认不满足 → 非应届。
    - has_grassroots：基层经历条件已满足 → true；不满足 → false。
    - party_status：政治面貌要求为「中共党员」且已满足 → 中共党员（其余措辞不猜）。
    - education：学历要求文本里能唯一识别层次 且 该条件已满足 → 对应层次。

    无法可靠推导的（性别、预估分、模考分）一律不导出，避免引擎用错值误解可报性。
    """
    statuses = checklist.statuses or {}
    cond_by_key = {c.key: c for c in checklist.conditions}
    pkg: dict = {}

    fg = cond_by_key.get("fresh_grad")
    if fg:
        st = statuses.get(fg.key) or "unmet"
        if st == "met":
            pkg["fresh_status"] = "应届"
        elif st == "unmet":
            pkg["fresh_status"] = "非应届"

    gr = cond_by_key.get("grassroots")
    if gr:
        st = statuses.get(gr.key) or "unmet"
        if st == "met":
            pkg["has_grassroots"] = True
        elif st == "unmet":
            pkg["has_grassroots"] = False

    pol = cond_by_key.get("political")
    if pol and (statuses.get(pol.key) or "unmet") == "met" and "中共党员" in pol.required:
        pkg["party_status"] = "中共党员"

    # 学历：唯一识别层次词，且该条条件已满足 → 才导出（避免多档要求时猜错档）
    edu = cond_by_key.get("education")
    if edu and (statuses.get(edu.key) or "unmet") == "met":
        hits = [_EDU_HINT_WORDS[w] for w in _EDU_HINT_WORDS if w in edu.required]
        if hits:
            pkg["education"] = hits[0]

    return pkg


def settle_checklist(db: Session, user_id: str) -> dict:
    """条件账本结算 — 回答用户真正的问题：我能不能报、还差什么、可补项怎么做。

    从用户最近核对的目标职位出发：
    1. 可报性结论：任一 hard_gate 条件未满足 → 这条锁死报考（该职位/专业）。
    2. 未满足清单：区分硬门槛（决定报不报）与可补项（决定怎么补），各带行动建议。
    3. 已满足概览：给一条"你还差什么"的诚实说明。

    纯规则、零 LLM。绝不武断：hard_gate 判定依赖措辞确定性（见 _classify_condition），
    无法可靠判定的条件标 unclassified 不参与可报性结论。
    """
    latest = (
        db.query(UserConditionStatus)
        .filter(UserConditionStatus.user_id == user_id)
        .order_by(UserConditionStatus.updated_at.desc())
        .first()
    )
    if not latest:
        return {
            "has_target": False,
            "verdict": "你还没有核对过任何目标职位。先去条件账本选定一个职位/专业，逐条勾选你的真实条件，这里就会给你「能不能报、还差什么」的答案。",
        }
    position = _load_position_ref(db, latest.exam_source, latest.position_id)
    if not position:
        return {
            "has_target": True,
            "verdict": "你最近核对的目标职位已不在当前批次，请重新选定一个职位。",
        }
    checklist = build_checklist_response(db, user_id, position)
    verdict_text, unmet = _verdict_and_unmet(checklist)
    return {
        "has_target": True,
        "exam_source": checklist.exam_source,
        "position_name": checklist.position_name,
        "dept_name": checklist.dept_name,
        "position_code": checklist.position_code,
        "progress": checklist.progress,
        "verdict": verdict_text,
        "unmet": unmet,
        "importable": _importable_package(checklist),
    }


def _load_position_ref(db: Session, exam_source: str, position_ref: str):
    """按勾选记录里的引用键反查职位对象（与 get_latest_condition_summary 同源）。"""
    import uuid as _uuid

    if exam_source == "kaoyan":
        try:
            return db.get(GradYanzhaoProgram, _uuid.UUID(position_ref))
        except (ValueError, AttributeError, TypeError):
            return None
    if exam_source == "province":
        return db.get(GwyProvincePosition, position_ref)
    return db.get(GwyPosition, position_ref)


def _verdict_and_unmet(checklist) -> tuple[str, list[dict]]:
    """根据清单状态生成可报性结论与未满足行动清单。"""
    hard_unmet = [
        {
            "key": c.key,
            "label": c.label,
            "required": c.required,
            "hint": _action_hint(c.key, c.category, c.required),
        }
        for c in checklist.conditions
        if c.category == "hard_gate" and (checklist.statuses.get(c.key) or "unmet") != "met"
    ]
    actionable_unmet = [
        {
            "key": c.key,
            "label": c.label,
            "required": c.required,
            "hint": _action_hint(c.key, c.category, c.required),
        }
        for c in checklist.conditions
        if c.category == "actionable" and (checklist.statuses.get(c.key) or "unmet") != "met"
    ]
    hard_met = sum(
        1
        for c in checklist.conditions
        if c.category == "hard_gate" and (checklist.statuses.get(c.key) or "unmet") == "met"
    )
    hard_total = sum(1 for c in checklist.conditions if c.category == "hard_gate")

    if hard_unmet:
        # 有硬门槛未满足 → 该职位/专业暂不可报，给出诚实结论
        gates = "、".join(u["label"] for u in hard_unmet)
        verdict = (
            f"这个目标当前暂不可报考：{gates} 未满足，是资格硬门槛。"
            "其余条件已满足也无法补救。建议改报不卡此项的同方向职位（或本科后 / 满足门槛后再报）。"
        )
    elif hard_total and hard_met == hard_total:
        if actionable_unmet:
            verdict = (
                "这个目标可报考的资格门槛你已全部满足。"
                "剩余的是可补项（分数/证书/考试），不影响报考资格，按行动建议补上即可提高上岸把握。"
            )
        else:
            verdict = "这个目标的硬性资格门槛你已全部满足，可以报考。"
    elif not hard_total:
        verdict = (
            "这个目标没有可自动判定的资格硬门槛（或门槛措辞开放，不武断）。"
            "建议对照职位原文逐条核对报考资格。"
        )
    else:
        verdict = "资格门槛有部分满足（进度见上），请在硬门槛未满足项上重点核对是否真实不满足。"

    unmet = {"hard_gate": hard_unmet, "actionable": actionable_unmet}
    return verdict, unmet
