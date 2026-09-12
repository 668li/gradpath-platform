# backend/app/services/data_search_service.py
"""站内数据搜索层 — AI 对话调用真实数据的统一入口（三段式）。

设计纪律（docs/AI技能内置规划-实现方案与候选清单-待拍板-2026-09-05.md）：
1. 代码级意图路由（detect_data_intents，零 LLM 调用，置信不足不查库）；
2. 确定性白名单查询（每类数据一条预定义查询，top-N 上限；绝不 text2sql）；
3. 带来源注入（[数据类型·表·来源URL·年份] 标注，查无数据如实明示，prompt 明令禁编）。

09-12 策略转向（信息差伴随层）：职位/考研复试线搜索器已随「不做职位库、
考研线不投入」拍板移除；保留公告（L2 核心，434 行真实在库）、薪资、市场面三类。
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.services.text_safety import sanitize_prompt_input

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 参数抽取（纯规则，置信不足返回 None → 上层跳过该搜索器）
# ---------------------------------------------------------------------------

_SCHOOL_RE = re.compile(r"([\u4e00-\u9fa5]{2,6}(?:大学|学院|研究院))")
_MAJOR_SUFFIX_RE = re.compile(r"([\u4e00-\u9fa5]{2,10})专业")

# 常见报考专业词表（公告标题/market/salary 的 LIKE 关键词）
_MAJOR_WHITELIST = [
    "计算机",
    "软件工程",
    "法学",
    "会计",
    "金融",
    "经济",
    "汉语言",
    "英语",
    "新闻",
    "土木",
    "电气",
    "机械",
    "临床",
    "护理",
    "行政管理",
    "工商管理",
    "统计学",
    "审计",
    "财政",
    "税务",
    "数学",
    "物理",
    "化学",
    "自动化",
    "电子信息",
    "通信",
    "法学类",
    "中国语言文学",
    "马克思主义",
]

# 国考热门部门词表（公告 content LIKE 关键词）
_DEPT_WHITELIST = [
    "税务",
    "海关",
    "公安",
    "法院",
    "检察院",
    "审计",
    "统计",
    "气象",
    "铁路",
    "邮政",
    "金融监管",
    "证监",
    "银保监",
    "财政",
    "边检",
    "移民",
    "海事",
    "粮食",
    "烟草",
]

# 校名前缀常见动词/虚词（匹配后从左剥离，防"我想考清华大学"整段被吞）
_SCHOOL_PREFIX_STOP = set("我想你要考报去读上冲问帮看看比和与跟对于在从把论说提确首推最")

# 专业候选里常见的学历/届别前缀（贪婪后缀正则会连着吞进来，"本科计算机"→"计算机"）
_MAJOR_PREFIXES = (
    "博士研究生",
    "硕士研究生",
    "研究生",
    "博士",
    "硕士",
    "本科",
    "专科",
    "大专",
    "应届",
    "往届",
)


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


def extract_major(text: str) -> str | None:
    m = _MAJOR_SUFFIX_RE.search(text)
    cand = m.group(1) if (m and len(m.group(1)) <= 10) else None
    if cand:
        # 剥离被贪婪正则误吞的校名与学历/动词前缀："清华大学计算机"→"计算机"
        for school in extract_schools(text):
            cand = cand.replace(school, "")
        changed = True
        while changed and cand:
            changed = False
            for p in _MAJOR_PREFIXES:
                if cand.startswith(p):
                    cand = cand[len(p) :]
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


def extract_dept(text: str) -> str | None:
    """抽部门词 — 多个命中时取文本中最早出现的（用户先说的优先）。"""
    found = [(text.find(d), d) for d in _DEPT_WHITELIST if d in text]
    if not found:
        return None
    return min(found)[1]


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

    domain: str  # announcements / salary / market
    params: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# 白名单搜索器 — 每类数据一条确定性预定义查询
# ---------------------------------------------------------------------------


def search_salary(db: Session, keyword: str | None, limit: int = 5) -> list[DataHit]:
    """薪资基准（salary_benchmarks）— 按岗位/公司关键词。"""
    from app.models.salary_benchmark import SalaryBenchmark

    if not keyword:
        return []
    rows = (
        db.query(SalaryBenchmark)
        .filter(
            SalaryBenchmark.position.like(f"%{keyword}%")
            | SalaryBenchmark.company.like(f"%{keyword}%")
        )
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
        .filter(
            MarketData.indicator.like(f"%{keyword}%") | MarketData.industry.like(f"%{keyword}%")
        )
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
        rows2 = q2.order_by(ExternalResearchItem.created_at.desc().nullslast()).limit(limit).all()
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
# 考试流程时间线（Phase1 Exam/ExamNode）— 诚实三态口径与前端 dateLabel 同源
# ---------------------------------------------------------------------------

STAGE_KEY_WORDS = (
    ("公告", "announce"),
    ("报名", "registration"),
    ("缴费", "payment"),
    ("准考证", "admission_ticket"),
    ("笔试", "written"),
    ("查分", "score"),
    ("出分", "score"),
    ("调剂", "adjustment"),
    ("面试", "interview"),
    ("体检", "medical"),
    ("政审", "political"),
    ("公示", "publicity"),
    ("录用", "hire"),
)


def _timeline_date_label(node: dict) -> str:
    """与前端 dateLabel（exam-timeline.tsx）同口径：绝不出现编造日期。入参为节点 payload 字典。"""
    status = node.get("date_status")
    status = status.value if hasattr(status, "value") else status
    planned = node.get("planned_date")
    end = node.get("planned_end_date")
    if status == "OFFICIAL" and planned:
        return f"官方：{planned.isoformat()}" + (f"~{end.isoformat()}" if end else "")
    if status == "PREDICTED" and planned:
        return (
            f"预计 {planned.isoformat()}"
            + (f"~{end.isoformat()}" if end else "")
            + "（公告后自动更新）"
        )
    return "日期待定（暂无可核验来源）"


def _pick_timeline_exam(db, track: str | None):
    """选考次：upcoming 优先（有未来动作），否则列表第一个。list_exams 返回字典列表。"""
    from app.services import timeline_service as tl

    exams = tl.list_exams(db, track=track)
    if not exams:
        return None
    upcoming = [e for e in exams if e.get("status") == "upcoming"]
    return (upcoming or exams)[0]


def _enum_val(v):
    return v.value if hasattr(v, "value") else v


def search_timeline(
    db: Session, stage_key: str | None = None, track: str | None = None, limit: int = 12
) -> list[DataHit]:
    """考试流程时间线节点（诚实三态：OFFICIAL 带源/PREDICTED 标预计/UNKNOWN 待定）。"""
    from app.services import timeline_service as tl

    exam = _pick_timeline_exam(db, track)
    if exam is None:
        return []
    try:
        detail = tl.get_exam_detail(db, exam["code"])
    except Exception as e:
        logger.warning("时间线详情读取失败: %s", e)
        return []

    nodes = list(detail.get("nodes") or [])
    if stage_key:
        nodes = [n for n in nodes if _enum_val(n.get("stage_key")) == stage_key]

    hits: list[DataHit] = []
    for n in nodes:
        date_part = _timeline_date_label(n)
        entry = f"；官方入口：{n.get('official_entry_url')}" if n.get("official_entry_url") else ""
        materials = ""
        if n.get("materials"):
            names = "、".join(
                str(m.get("name")) for m in n["materials"] if isinstance(m, dict) and m.get("name")
            )
            materials = f"；需备材料：{names}" if names else ""
        hits.append(
            DataHit(
                title=f"{detail.get('name')}·{n.get('title')}",
                content=f"{n.get('title')}（{date_part}）{entry}{materials}",
                source_table="t_exam_node",
                url=n.get("official_entry_url") or n.get("source_url") or "",
            )
        )
    return hits[:limit]


# ---------------------------------------------------------------------------
# 代码级意图路由 — 零 LLM 调用，置信不足不查库
# ---------------------------------------------------------------------------

_SALARY_WORDS = ("薪资", "工资", "待遇", "年薪", "月薪", "薪酬", "挣多少", "赚多少")
_MARKET_WORDS = ("就业前景", "就业面", "行业趋势", "市场行情")
_ANNOUNCE_WORDS = ("公告", "简章", "招生信息", "招考通知")
# 时间线意图用短语级词表，避免"面试/体检"这类单词误劫持其他 skill 的对话
_TIMELINE_WORDS = (
    "时间线",
    "考试流程",
    "到哪一步",
    "报名截止",
    "报名时间",
    "准考证",
    "笔试时间",
    "查分时间",
    "国考时间",
    "省考时间",
    "考试安排",
    "流程是什么",
)


def detect_data_intents(content: str) -> list[DataIntent]:
    """从用户消息中检测数据搜索意图（纯规则）。

    没有可抽参数的高频意图返回空——诚实降级，绝不盲目查库。
    """
    text = content or ""
    intents: list[DataIntent] = []
    schools = extract_schools(text)
    major = extract_major(text)

    if any(w in text for w in _ANNOUNCE_WORDS):
        # 公告查询无关键词也能查（返回最新几条），不需要置信门槛
        intents.append(DataIntent("announcements", {"keyword": schools[0] if schools else major}))
    if any(w in text for w in _TIMELINE_WORDS):
        track = "shengkao" if "省考" in text else ("guokao" if "国考" in text else None)
        stage = next((k for w, k in STAGE_KEY_WORDS if w in text), None)
        intents.append(DataIntent("timeline", {"stage_key": stage, "track": track}))
    if any(w in text for w in _SALARY_WORDS):
        intents.append(DataIntent("salary", {"keyword": major}))
    if any(w in text for w in _MARKET_WORDS):
        intents.append(DataIntent("market", {"keyword": major or extract_dept(text)}))
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
            if intent.domain == "announcements":
                found = search_announcements(db, intent.params.get("keyword"))
            elif intent.domain == "timeline":
                found = search_timeline(
                    db,
                    stage_key=intent.params.get("stage_key"),
                    track=intent.params.get("track"),
                )
            elif intent.domain == "salary":
                found = search_salary(db, intent.params.get("keyword"))
            elif intent.domain == "market":
                found = search_market(db, intent.params.get("keyword"))
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
            "请如实告知用户站内暂无此数据，并建议其前往对应官方渠道查询，"
            "禁止编造任何分数线、职位数、薪资数字。"
        )
        return block, [], False

    lines = [
        "【站内数据检索结果】以下是 GradPath 数据库真实记录，回答必须基于这些数据；",
        "数据库没有的信息如实说「暂无数据」，禁止编造。每条末尾为来源。",
        "",
    ]
    sources: list[dict] = []
    for i, h in enumerate(hits[:8], 1):
        label = f"{h.source_table}" + (f"·{h.year}年" if h.year else "")
        src_tag = f"（来源: {h.url}）" if h.url else f"（来源: 站内数据库 {label}）"
        lines.append(f"{i}. {h.content[:_HIT_CONTENT_MAX]} [{label}]{src_tag}")
        sources.append(
            {"type": "db", "title": h.title[:40], "content": h.content[:120], "url": h.url}
        )
    lines.append("")
    lines.append("（以上按数据库最新收录年份倒序；若与用户问题不完全对口，请说明数据边界。）")

    block = sanitize_prompt_input("\n".join(lines))
    return block, sources, True
