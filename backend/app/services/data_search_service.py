# backend/app/services/data_search_service.py
"""站内数据搜索层 — AI 对话调用真实数据的统一入口（三段式）。

设计纪律（docs/AI技能内置规划-实现方案与候选清单-待拍板-2026-09-05.md）：
1. 代码级意图路由（detect_data_intents，零 LLM 调用，置信不足不查库）；
2. 确定性白名单查询（每类数据一条预定义查询，top-N 上限；绝不 text2sql）；
3. 带来源注入（[数据类型·表·来源URL·年份] 标注，查无数据如实明示，prompt 明令禁编）。

三处复用：chat 通用链路（本轮）+ 数据型 skill 的 inject_data（择校对话师/选岗参谋）。
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.services.text_safety import sanitize_prompt_input

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 参数抽取（纯规则，置信不足返回 None → 上层跳过该搜索器）
# ---------------------------------------------------------------------------

_SCHOOL_RE = re.compile(r"([\u4e00-\u9fa5]{2,6}(?:大学|学院|研究院))")
_SCORE_RE = re.compile(r"(\d{3})\s*分")
_MAJOR_SUFFIX_RE = re.compile(r"([\u4e00-\u9fa5]{2,10})专业")

_EDUCATION_MAP = [
    ("博士", "博士"),
    ("硕士研究生", "硕士"),
    ("硕士", "硕士"),
    ("研究生", "硕士"),
    ("专科", "专科"),
    ("大专", "专科"),
    ("本科", "本科"),
    ("学士学位", "本科"),
]

# 常见报考专业词表（岗位 major_req / 进面线 major_name 的 LIKE 关键词）
_MAJOR_WHITELIST = [
    "计算机", "软件工程", "法学", "会计", "金融", "经济", "汉语言", "英语",
    "新闻", "土木", "电气", "机械", "临床", "护理", "行政管理", "工商管理",
    "统计学", "审计", "财政", "税务", "数学", "物理", "化学", "自动化",
    "电子信息", "通信", "法学类", "中国语言文学", "马克思主义",
]

# 国考热门部门词表（dept_name LIKE 关键词）
_DEPT_WHITELIST = [
    "税务", "海关", "公安", "法院", "检察院", "审计", "统计", "气象",
    "铁路", "邮政", "金融监管", "证监", "银保监", "财政", "边检", "移民",
    "海事", "粮食", "烟草",
]

_PROVINCES = [
    "北京", "天津", "河北", "山西", "内蒙古", "辽宁", "吉林", "黑龙江",
    "上海", "江苏", "浙江", "安徽", "福建", "江西", "山东", "河南", "湖北",
    "湖南", "广东", "广西", "海南", "重庆", "四川", "贵州", "云南", "西藏",
    "陕西", "甘肃", "青海", "宁夏", "新疆",
]

# 学历档与职位表 education_req 文本的匹配规则（education_req 官方文本如
# "仅限本科""本科及以上""硕士研究生及以上"）
_EDU_LIKE = {
    "专科": "大专",
    "本科": "本科",
    "硕士": "研究生",
    "博士": "博士",
}

# 判别 intel 枚举值 → 中文
_DISCRIMINATION_ZH = {
    "none": "不卡", "light": "轻微", "moderate": "中等",
    "severe": "严重", "unknown": "未知",
}
_PROTECTION_ZH = {"yes": "是", "partial": "部分", "no": "否", "unknown": "未知"}


# 校名前缀常见动词/虚词（匹配后从左剥离，防"我想考清华大学"整段被吞）
_SCHOOL_PREFIX_STOP = set("我想你要考报去读上冲问帮看看比和与跟对于在从把论说提确首推最")


def extract_schools(text: str) -> list[str]:
    """抽校名候选（如 清华大学/中南大学）。

    中文无词边界，正则容易把前置口语吞进候选（"我想考清华大学"），
    故限制校名主体 2-6 字并从左剥离常见动词/虚词前缀。
    """
    out: list[str] = []
    for span in _SCHOOL_RE.findall(text):
        while len(span) > 2 and span[0] in _SCHOOL_PREFIX_STOP:
            span = span[1:]
        if 2 <= len(span) <= 10:
            out.append(span)
    return list(dict.fromkeys(out))[:3]


# 专业候选里常见的学历/届别前缀（贪婪后缀正则会连着吞进来，"本科计算机"→"计算机"）
_MAJOR_PREFIXES = (
    "博士研究生", "硕士研究生", "研究生", "博士", "硕士",
    "本科", "专科", "大专", "应届", "往届",
)


def extract_major(text: str) -> str | None:
    m = _MAJOR_SUFFIX_RE.search(text)
    cand = m.group(1) if (m and len(m.group(1)) <= 10) else None
    if cand:
        # 剥离被贪婪正则误吞的校名与动词前缀："清华大学计算机"→"计算机"
        for school in extract_schools(text):
            cand = cand.replace(school, "")
        changed = True
        while changed and cand:
            changed = False
            for p in _MAJOR_PREFIXES:
                if cand.startswith(p):
                    cand = cand[len(p):]
                    changed = True
                    break
            if cand and cand[0] in _SCHOOL_PREFIX_STOP:
                cand = cand[1:]
                changed = True
        cand = cand.strip()
    if cand:
        return cand
    for kw in _MAJOR_WHITELIST:
        if kw in text:
            return kw
    return None


def extract_education(text: str) -> str | None:
    for kw, edu in _EDUCATION_MAP:
        if kw in text:
            return edu
    return None


def extract_province(text: str) -> str | None:
    for p in _PROVINCES:
        if p in text:
            return p
    return None


def extract_dept(text: str) -> str | None:
    """抽部门词 — 多个命中时取文本中最早出现的（用户先说的优先）。"""
    found = [(text.find(d), d) for d in _DEPT_WHITELIST if d in text]
    if not found:
        return None
    return min(found)[1]


def extract_score(text: str) -> int | None:
    m = _SCORE_RE.search(text)
    return int(m.group(1)) if m else None


# ---------------------------------------------------------------------------
# 统一结果结构
# ---------------------------------------------------------------------------


@dataclass
class DataHit:
    """一条站内数据命中 — 统一携带溯源信息。"""

    title: str
    content: str
    source_table: str
    url: str = ""
    year: int | None = None


@dataclass
class DataIntent:
    """一个待执行的搜索意图。"""

    domain: str  # score_lines / school_intel / positions / salary / market
    params: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# 白名单搜索器 — 每类数据一条确定性预定义查询
# ---------------------------------------------------------------------------


def search_score_lines(db: Session, school: str | None, major: str | None, limit: int = 6) -> list[DataHit]:
    """真实复试分数线（grad_scoreline_records）— total_score_line>0 过滤脏数据。"""
    from app.models.grad_intel import GradScorelineRecord

    q = db.query(GradScorelineRecord).filter(GradScorelineRecord.total_score_line > 0)
    if school:
        q = q.filter(GradScorelineRecord.university_name.like(f"%{school}%"))
    if major:
        q = q.filter(GradScorelineRecord.major_name.like(f"%{major}%"))
    if not school and not major:
        return []
    rows = q.order_by(GradScorelineRecord.year.desc()).limit(limit).all()

    hits: list[DataHit] = []
    for r in rows:
        parts = [f"{r.year}年 {r.university_name} {r.major_name}"]
        if r.degree_type:
            parts.append(f"({r.degree_type})")
        parts.append(f"复试总分线 {r.total_score_line}")
        singles = [
            s for s in (
                r.politics_score, r.foreign_language_score,
                r.business_1_score, r.business_2_score,
            ) if s
        ]
        if singles:
            parts.append(f"单科 {('/').join(str(s) for s in singles)}")
        if r.enrollment_count:
            parts.append(f"录取 {r.enrollment_count} 人")
        if r.application_count:
            parts.append(f"报考 {r.application_count} 人")
        url = ""
        for src in r.data_sources or []:
            if isinstance(src, dict) and src.get("url"):
                url = src["url"]
                break
        hits.append(
            DataHit(title=f"{r.university_name} {r.major_name} {r.year}复试线",
                    content="，".join(str(p) for p in parts),
                    source_table="grad_scoreline_records", url=url, year=r.year)
        )
    return hits


def search_school_intel(db: Session, school: str, limit: int = 4) -> list[DataHit]:
    """院校情报（grad_school_intel）— 报录比/推免/卡学历/复试占比。"""
    from app.models.grad_intel import GradSchoolIntel

    rows = (
        db.query(GradSchoolIntel)
        .filter(GradSchoolIntel.school_name.like(f"%{school}%"))
        .limit(limit)
        .all()
    )
    hits: list[DataHit] = []
    for r in rows:
        parts = [f"{r.school_name} {r.major_name}（{r.year}）"]
        if r.admission_ratio:
            parts.append(f"报录比 {r.admission_ratio}")
        if r.push_ratio:
            parts.append(f"推免占比 {r.push_ratio}")
        if r.actual_quota:
            parts.append(f"统考名额 {r.actual_quota}")
        if r.retest_weight:
            parts.append(f"复试占比 {r.retest_weight}")
        parts.append(f"卡第一学历: {_DISCRIMINATION_ZH.get(r.background_discrimination, r.background_discrimination)}")
        parts.append(f"保护一志愿: {_PROTECTION_ZH.get(r.first_choice_protection, r.first_choice_protection)}")
        if r.score_suppression not in ("unknown", ""):
            parts.append("存在压分" if r.score_suppression == "yes" else "无明显压分")
        hits.append(
            DataHit(title=f"{r.school_name} {r.major_name} 院校情报",
                    content="，".join(parts),
                    source_table="grad_school_intel")
        )
    return hits


def search_positions(
    db: Session,
    education: str | None = None,
    province: str | None = None,
    dept: str | None = None,
    major: str | None = None,
    limit: int = 10,
) -> list[DataHit]:
    """公务员职位（gwy_position + gwy_province_position）— 最新年份，附进面分。"""
    from app.models.gwy_position import GwyPosition
    from app.models.gwy_province_position import GwyProvincePosition
    from app.models.gwy_score_line import GwyScoreLine

    hits: list[DataHit] = []
    edu_like = _EDU_LIKE.get(education) if education else None
    per_source = max(limit // 2, 3)

    # --- 国考 ---
    try:
        year = db.query(GwyPosition.year).order_by(GwyPosition.year.desc()).first()
        if year:
            latest_year = year[0]
            q = db.query(GwyPosition).filter(GwyPosition.year == latest_year)
            if edu_like:
                q = q.filter(GwyPosition.education_req.like(f"%{edu_like}%"))
            if province:
                q = q.filter(GwyPosition.work_location.like(f"%{province}%"))
            if dept:
                q = q.filter(GwyPosition.dept_name.like(f"%{dept}%"))
            if major:
                q = q.filter(GwyPosition.major_req.like(f"%{major}%"))
            rows = q.order_by(GwyPosition.recruit_count.desc().nullslast()).limit(per_source).all()

            codes = [r.position_code for r in rows]
            line_map: dict[str, float] = {}
            if codes:
                lines = (
                    db.query(GwyScoreLine)
                    .filter(
                        GwyScoreLine.year == latest_year,
                        GwyScoreLine.position_code.in_(codes),
                        GwyScoreLine.min_score.isnot(None),
                    )
                    .all()
                )
                for ln in lines:
                    line_map.setdefault(ln.position_code, ln.min_score)
            for r in rows:
                parts = [f"【国考{latest_year}】{r.dept_name or ''} · {r.position_name or ''}"]
                if r.work_location:
                    parts.append(f"工作地 {r.work_location}")
                if r.recruit_count:
                    parts.append(f"招 {r.recruit_count} 人")
                if r.education_req:
                    parts.append(f"学历 {r.education_req}")
                if r.major_req:
                    parts.append(f"专业 {r.major_req[:60]}")
                if r.position_code in line_map:
                    parts.append(f"去年进面最低分 {line_map[r.position_code]:g}")
                hits.append(
                    DataHit(title=f"国考{latest_year} {r.position_name or r.position_code}",
                            content="，".join(p for p in parts if p),
                            source_table="gwy_position",
                            url=r.source_url or "", year=latest_year)
                )
    except Exception as e:
        logger.warning("国考职位搜索失败: %s", e)

    # --- 省考 ---
    try:
        year = db.query(GwyProvincePosition.year).order_by(GwyProvincePosition.year.desc()).first()
        if year:
            latest_year = year[0]
            q = db.query(GwyProvincePosition).filter(GwyProvincePosition.year == latest_year)
            if province:
                q = q.filter(GwyProvincePosition.province == province)
            if edu_like:
                q = q.filter(GwyProvincePosition.education_req.like(f"%{edu_like}%"))
            if dept:
                cond = GwyProvincePosition.dept_name.like(f"%{dept}%")
                q = q.filter(cond)
            if major:
                major_cond = (
                    GwyProvincePosition.major_req_grad.like(f"%{major}%")
                    | GwyProvincePosition.major_req_undergrad.like(f"%{major}%")
                    | GwyProvincePosition.major_req_junior.like(f"%{major}%")
                )
                q = q.filter(major_cond)
            rows = q.order_by(GwyProvincePosition.recruit_count.desc().nullslast()).limit(per_source).all()
            for r in rows:
                parts = [f"【{r.province}省考{latest_year}】{r.dept_name or ''} · {r.position_name or ''}"]
                if r.recruit_count:
                    parts.append(f"招 {r.recruit_count} 人")
                if r.education_req:
                    parts.append(f"学历 {r.education_req}")
                if r.exam_region:
                    parts.append(f"考区 {r.exam_region}")
                hits.append(
                    DataHit(title=f"{r.province}省考 {r.position_name or r.position_code}",
                            content="，".join(p for p in parts if p),
                            source_table="gwy_province_position",
                            url=r.source_url or "", year=latest_year)
                )
    except Exception as e:
        logger.warning("省考职位搜索失败: %s", e)
    return hits[:limit]


def search_salary(db: Session, keyword: str | None, limit: int = 5) -> list[DataHit]:
    """薪资基准（salary_benchmarks）— 按岗位/公司关键词。"""
    from app.models.salary_benchmark import SalaryBenchmark

    if not keyword:
        return []
    rows = (
        db.query(SalaryBenchmark)
        .filter(SalaryBenchmark.position.like(f"%{keyword}%") | SalaryBenchmark.company.like(f"%{keyword}%"))
        .limit(limit)
        .all()
    )
    return [
        DataHit(
            title=f"{r.company} {r.position} 薪资",
            content=f"{r.company} {r.position}（{r.city or ''}，{getattr(r.experience_level, 'value', r.experience_level)}）："
                    f"中位数 {r.salary_median}（{r.salary_min}~{r.salary_max}），来源 {r.source} {r.year}",
            source_table="salary_benchmarks",
            year=r.year,
        )
        for r in rows
    ]


def search_market(db: Session, keyword: str | None, limit: int = 5) -> list[DataHit]:
    """就业市场面（market_data）— 行业指标。"""
    from app.models.market_data import MarketData

    if not keyword:
        return []
    rows = (
        db.query(MarketData)
        .filter(MarketData.indicator.like(f"%{keyword}%") | MarketData.industry.like(f"%{keyword}%"))
        .order_by(MarketData.year.desc())
        .limit(limit)
        .all()
    )
    return [
        DataHit(
            title=f"{r.indicator}（{r.year}）",
            content=f"{r.indicator} = {r.value:g}{r.unit}（{r.category}，{r.industry or '全行业'}，{r.region or '全国'}），来源 {r.source}",
            source_table="market_data",
            url=r.source_url or "",
            year=r.year,
        )
        for r in rows
    ]


def search_announcements(db: Session, keyword: str | None = None, limit: int = 3) -> list[DataHit]:
    """官方公告（kaoyan_news 正式表 official 来源；暂存表 APPROVED 兜底）。

    正式表尚无 official 行时降级查暂存表（审核晋升前的合法数据源），
    两处都空返回 []——由上层明示「暂无已收录公告」，绝不编造公告内容。
    """
    hits: list[DataHit] = []
    try:
        from app.models.kaoyan_news import KaoyanNews

        q = db.query(KaoyanNews).filter(
            KaoyanNews.status == "approved",
            KaoyanNews.source_platform == "official",
        )
        if keyword:
            q = q.filter(
                KaoyanNews.title.like(f"%{keyword}%")
                | KaoyanNews.content.like(f"%{keyword}%")
                | KaoyanNews.category.like(f"%{keyword}%")
            )
        rows = (
            q.order_by(KaoyanNews.published_at.desc().nullslast(), KaoyanNews.crawled_at.desc())
            .limit(limit)
            .all()
        )
        for r in rows:
            published = r.published_at.strftime("%Y-%m-%d") if r.published_at else "日期未知"
            body = (r.summary or r.content or "")[:220]
            hits.append(
                DataHit(
                    title=r.title[:80],
                    content=f"《{r.title}》（{published}，{r.category or ''}）：{body}",
                    source_table="kaoyan_news",
                    url=r.source_url or "",
                    year=r.published_at.year if r.published_at else None,
                )
            )
    except Exception as e:
        logger.warning("公告正式表搜索失败: %s", e)

    if hits:
        return hits

    # 暂存表兜底（审核晋升前）
    try:
        from app.models.ingestion import ExternalResearchItem

        q2 = db.query(ExternalResearchItem).filter(
            ExternalResearchItem.source_platform == "official",
            ExternalResearchItem.review_status == "APPROVED",
        )
        if keyword:
            q2 = q2.filter(
                ExternalResearchItem.title.like(f"%{keyword}%")
                | ExternalResearchItem.content.like(f"%{keyword}%")
            )
        rows2 = (
            q2.order_by(ExternalResearchItem.created_at.desc().nullslast()).limit(limit).all()
        )
        for r in rows2:
            body = (r.content or "")[:220]
            hits.append(
                DataHit(
                    title=(r.title or "")[:80],
                    content=f"《{r.title}》：{body}",
                    source_table="t_external_research_item",
                    url=r.source_url or "",
                )
            )
    except Exception as e:
        logger.warning("公告暂存表搜索失败: %s", e)
    return hits


# ---------------------------------------------------------------------------
# 代码级意图路由 — 零 LLM 调用，置信不足不查库
# ---------------------------------------------------------------------------

_SCORELINE_WORDS = ("分数线", "进面线", "复试线", "录取分", "多少分")
_INTEL_WORDS = ("报录比", "推免", "保护一志愿", "卡本科", "卡第一学历", "歧视", "压分", "复试占比", "统考名额")
_POSITION_WORDS = ("职位", "岗位", "招录", "招考", "国考", "省考", "公务员", "报考条件")
_SALARY_WORDS = ("薪资", "工资", "待遇", "年薪", "月薪", "薪酬", "挣多少", "赚多少")
_MARKET_WORDS = ("就业前景", "就业面", "行业趋势", "市场行情")
_ANNOUNCE_WORDS = ("公告", "简章", "招生信息", "招考通知")


def detect_data_intents(content: str) -> list[DataIntent]:
    """从用户消息中检测数据搜索意图（纯规则）。

    返回按优先级排序的意图列表（调用方执行时截断）。
    没有可抽参数的高频意图（如只说"分数线"无校名专业）返回空——诚实降级，
    由 skill 的澄清话术引导用户补参数，绝不盲目查库。
    """
    text = content or ""
    intents: list[DataIntent] = []
    schools = extract_schools(text)
    major = extract_major(text)

    if any(w in text for w in _SCORELINE_WORDS) and (schools or major):
        intents.append(DataIntent("score_lines", {"school": schools[0] if schools else None, "major": major}))
    if (any(w in text for w in _INTEL_WORDS) and schools) or (schools and any(w in text for w in ("考研", "报考", "考"))):
        intents.append(DataIntent("school_intel", {"school": schools[0]}))
    if any(w in text for w in _POSITION_WORDS):
        dept = extract_dept(text)
        major = extract_major(text)
        # 部门词与专业词同词时（"税务岗位"的"税务"），该词是部门不是专业，
        # 保留会把 major_req LIKE '%税务%' 叠加成零命中（生产实证 11545→0）
        if major and dept and major == dept:
            major = None
        intents.append(
            DataIntent(
                "positions",
                {
                    "education": extract_education(text),
                    "province": extract_province(text),
                    "dept": dept,
                    "major": major,
                },
            )
        )
    if any(w in text for w in _SALARY_WORDS):
        intents.append(DataIntent("salary", {"keyword": major}))
    if any(w in text for w in _MARKET_WORDS):
        intents.append(DataIntent("market", {"keyword": major or extract_dept(text)}))
    if any(w in text for w in _ANNOUNCE_WORDS):
        # 公告查询无关键词也能查（返回最新几条），不需要置信门槛
        intents.append(DataIntent("announcements", {"keyword": schools[0] if schools else major}))
    return intents


# ---------------------------------------------------------------------------
# 执行入口 — 返回（注入文本块, 前端 sources, 是否有命中）
# ---------------------------------------------------------------------------

_MAX_INTENTS_PER_TURN = 2
_HIT_CONTENT_MAX = 180


def run_data_search(
    db: Session,
    content: str,
    skip_domains: set[str] | frozenset[str] = frozenset(),
) -> tuple[str, list[dict], bool]:
    """执行站内数据搜索并生成可注入 system prompt 的文本块。

    Returns:
        (injection_block, agent_sources, has_hits)
        - injection_block: 直接追加到 system prompt 的【站内数据检索结果】文本，无意图时为 ""
        - agent_sources: 前端消息气泡"参考来源"标签数据（[{type,title,content,url}]）
        - has_hits: 是否有真实命中（False 但检测到意图 → 明示"暂无数据"块）
    """
    intents = [i for i in detect_data_intents(content) if i.domain not in skip_domains]
    if not intents:
        return "", [], False

    hits: list[DataHit] = []
    executed = 0
    for intent in intents[:_MAX_INTENTS_PER_TURN]:
        try:
            if intent.domain == "score_lines":
                found = search_score_lines(db, intent.params.get("school"), intent.params.get("major"))
            elif intent.domain == "school_intel":
                found = search_school_intel(db, intent.params["school"])
            elif intent.domain == "positions":
                found = search_positions(
                    db,
                    education=intent.params.get("education"),
                    province=intent.params.get("province"),
                    dept=intent.params.get("dept"),
                    major=intent.params.get("major"),
                )
            elif intent.domain == "salary":
                found = search_salary(db, intent.params.get("keyword"))
            elif intent.domain == "market":
                found = search_market(db, intent.params.get("keyword"))
            elif intent.domain == "announcements":
                found = search_announcements(db, intent.params.get("keyword"))
            else:
                found = []
            hits.extend(found)
            executed += 1
        except Exception as e:
            logger.warning("数据搜索器 %s 执行失败: %s", intent.domain, e)

    # 意图命中但查无数据 → 明示空结果，杜绝模型编数
    if not hits:
        block = (
            "【站内数据检索结果】\n"
            f"已检索站内数据库（{executed} 类），未找到与该问题直接相关的记录。"
            "请如实告知用户站内暂无此数据，可建议用户补充院校/专业/地区等关键词，"
            "禁止编造任何分数线、职位数、薪资数字。"
        )
        return block, [], False

    lines = ["【站内数据检索结果】以下是 GradPath 数据库真实记录，回答必须基于这些数据；", "数据库没有的信息如实说「暂无数据」，禁止编造。每条末尾为来源。", ""]
    sources: list[dict] = []
    for i, h in enumerate(hits[:8], 1):
        label = f"{h.source_table}" + (f"·{h.year}年" if h.year else "")
        src_tag = f"（来源: {h.url}）" if h.url else f"（来源: 站内数据库 {label}）"
        lines.append(f"{i}. {h.content[:_HIT_CONTENT_MAX]} [{label}]{src_tag}")
        sources.append({"type": "db", "title": h.title[:40], "content": h.content[:120], "url": h.url})
    lines.append("")
    lines.append("（以上按数据库最新收录年份倒序；若与用户问题不完全对口，请说明数据边界。）")

    block = sanitize_prompt_input("\n".join(lines))
    return block, sources, True
