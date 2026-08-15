"""经验贴质量分级 + 反软广检测 + 结构化元信息抽取（Phase G）。

与 quality.py（资讯质量分）并列：资讯侧重信源权威度/时效，经验贴侧重
来源可信度/内容完整度/互动信号/可溯源/反软广 —— 因为经验的价值来自
"真实上岸者的具体做法"，而非官方信源。软广经验贴（引流/卖课/包过）
会被标注（is_promotion=True）但不下架：管理员已人工审核通过，标注让
前端用户知情，同时反软广维度拉低质量分（排序降权）。

纯规则本地计算（零 LLM 成本）：入库审核确认时调用；LLM 增强见
services/experience_enhance.py（挂载点，本轮不启用）。
"""
import re
from urllib.parse import urlparse

from app.crawlers.research.quality import grade_of
from app.crawlers.research.transformer import STAGE_KEYWORDS, SUBJECT_KEYWORDS

# ----------------------------------------------------------------------
# 反软广检测
# ----------------------------------------------------------------------
# 强营销词：承诺效果 / 售卖性质（命中即高置信度标注）
_STRONG_MARKETING = [
    "包过", "保过", "保录", "内部资料", "押题", "保真", "保录取",
    "免试入学", "不过退费", "定金", "名额有限", "最后名额", "限时优惠",
]
# 引流词：引导私信/加群/领资料（命中即标注）
_LEAD_GEN = [
    "加微信", "加v", "加我vx", "私信", "领取资料", "领资料",
    "扫码", "二维码", "进群", "qq群", "扣扣", "微信公众号",
]
# 售卖词：机构/课程/付费（辅助判定，提高置信度）
_PROMO_WORDS = [
    "优惠", "价格", "报名费", "课程", "培训班", "辅导机构", "机构",
    "辅导班", "一对一", "网课", "低价", "免费领取", "资料包", "套餐",
]

# 具体证据标记：标题/正文出现院校名或分数（有"干货"的证据，降低误伤）
_SCHOOL_RE = re.compile(r"[\u4e00-\u9fff]{2,10}?(?:大学|学院|研究院|党校)")
_SCORE_RE = re.compile(r"\d{3}\s*分")


def detect_promotion(
    title: str,
    content: str,
    tags: list[str] | None = None,
) -> tuple[bool, float, str]:
    """软广/引流检测。

    Returns:
        (is_promotion, confidence 0-1, reason)

    判定逻辑：命中强营销词或引流词即标注；命中售卖词辅助加置信度；
    无具体证据（无院校名、无分数）时置信度上浮（更像纯引流号）。
    """
    text = f"{title or ''}\n{(content or '')[:2000]}"
    if tags:
        text += "\n" + " ".join(str(t) for t in tags if isinstance(t, str))
    text_lower = text.lower()

    hits: list[str] = []
    for kw in _STRONG_MARKETING:
        if kw.lower() in text_lower and kw not in hits:
            hits.append(kw)
    for kw in _LEAD_GEN:
        if kw.lower() in text_lower and kw not in hits:
            hits.append(kw)
    for kw in _PROMO_WORDS:
        if kw.lower() in text_lower and kw not in hits:
            hits.append(kw)

    if not hits:
        return False, 0.0, ""

    # 置信度：首类命中给 0.5 底分，每条命中 +0.05（去重后），封顶 0.95
    confidence = min(0.95, 0.5 + 0.05 * len(hits))
    # 无具体证据（无院校名/分数/学科词）→ 更可能是纯引流号，置信度上浮
    has_evidence = bool(
        _SCHOOL_RE.search(text)
        or _SCORE_RE.search(text)
        or any(kw.lower() in text_lower for kw in SUBJECT_KEYWORDS)
    )
    if not has_evidence:
        confidence = min(0.95, confidence + 0.15)

    reason = "疑似软广:" + ",".join(hits[:8])
    return True, round(confidence, 2), reason


# ----------------------------------------------------------------------
# 结构化元信息抽取（方法/适用人群/学科/阶段/院校/目标分）
# ----------------------------------------------------------------------
# 学习方法类关键词（经验的价值维度：可执行方法而非空话）
_METHOD_KEYWORDS = [
    "计划", "时间表", "作息", "刷题", "真题", "笔记", "错题", "复盘",
    "背诵", "记忆", "思维导图", "网课", "基础班", "强化", "冲刺",
    "单词", "长难句", "模拟考", "模考", "复盘", "框架",
]
# 适用人群关键词
_AUDIENCE_KEYWORDS = [
    "一战", "二战", "三战", "在职", "跨考", "跨专业", "零基础",
    "应届", "往届", "脱产",
]
# 院校名：上岸/录取/报考/考取 后的院校，或正文任意院校名
_SCHOOL_AFTER = re.compile(
    r"(?:上岸|录取|考入|考取|报考|目标|拟录取)\s*"
    r"([\u4e00-\u9fff]{2,10}?(?:大学|学院|研究院|党校))"
)
_ANY_SCHOOL = re.compile(r"([\u4e00-\u9fff]{2,10}?(?:大学|学院|研究院|党校))")
# 目标分：初试/总分/各科 分数
_SCORE_TARGET = re.compile(
    r"(?:初试|总分|目标|考了|最终|政治|英语|数学|专业课)[^。；\n]{0,10}?"
    r"(?:约|考)?\s*(\d{3})\s*分"
)


def _first_match(keywords: list[str], text_lower: str) -> str | None:
    for kw in keywords:
        if kw.lower() in text_lower:
            return kw
    return None


def extract_experience_meta(
    title: str,
    content: str,
    tags: list[str] | None = None,
) -> dict:
    """从标题+正文+标签抽取结构化元信息（规则版，全部 JSON 安全）。

    返回：{"subject": str|None, "stage": str|None, "school": str|None,
           "target_score": int|None, "methods": [str], "audience": str|None}
    无命中字段为 None / []，前端按需渲染（诚实，不编造）。
    """
    text = f"{title or ''}\n{(content or '')[:3000]}"
    text_lower = text.lower()

    subject = _first_match(SUBJECT_KEYWORDS, text_lower)
    stage = _first_match(STAGE_KEYWORDS, text_lower)
    audience = _first_match(_AUDIENCE_KEYWORDS, text_lower)

    school = None
    m = _SCHOOL_AFTER.search(text)
    if m:
        school = m.group(1).strip()
    else:
        m = _ANY_SCHOOL.search(text)
        if m:
            school = m.group(1).strip()

    target_score = None
    m = _SCORE_TARGET.search(text)
    if m:
        try:
            target_score = int(m.group(1))
        except (TypeError, ValueError):
            target_score = None

    methods = [kw for kw in _METHOD_KEYWORDS if kw.lower() in text_lower]
    # 去重保序，限制条数
    seen: set[str] = set()
    methods_unique: list[str] = []
    for kw in methods:
        if kw not in seen:
            seen.add(kw)
            methods_unique.append(kw)
    methods = methods_unique[:8]

    return {
        "subject": subject,
        "stage": stage,
        "school": school,
        "target_score": target_score,
        "methods": methods,
        "audience": audience,
    }


# ----------------------------------------------------------------------
# 经验贴质量打分（0-100 + A/B/C/D）
# ----------------------------------------------------------------------
_OFFICIAL_SUFFIXES = (".edu.cn", ".gov.cn", ".ac.cn")

# 来源可信度（总分 30）：官方转载 > 社区（B站/知乎）> 站内投稿 > 其他
_TRUST_OFFICIAL = 25
_TRUST_COMMUNITY = 20
_TRUST_USER = 15
_TRUST_OTHER = 12
# 内容完整度（总分 30）：正文越长干货可能越多（经验贴价值来自具体做法）
_COMPLETE_MAX = 30
# 互动信号（总分 20）：外部播放/点赞是真实用户投票
_ENGAGE_MAX = 20
# 可溯源（总分 10）
_TRACEABLE = 10
# 反软广（总分 10）：非推广才给满分
_ANTI_PROMO = 10

_COMMUNITY_PLATFORMS = {"bilibili", "zhihu", "bilibili_research"}


def _trust_score(source_url: str, source_platform: str) -> int:
    hostname = (urlparse(source_url or "").hostname or "").lower()
    if any(hostname.endswith(s) for s in _OFFICIAL_SUFFIXES):
        return _TRUST_OFFICIAL
    if source_platform in _COMMUNITY_PLATFORMS or any(
        hostname == d or hostname.endswith("." + d)
        for d in ("bilibili.com", "zhihu.com")
    ):
        return _TRUST_COMMUNITY
    if source_platform in ("user", "") or source_platform is None:
        return _TRUST_USER
    return _TRUST_OTHER


def _completeness_score(content: str) -> int:
    content = content or ""
    if len(content) >= 1000:
        return _COMPLETE_MAX
    if len(content) >= 500:
        return 24
    if len(content) >= 200:
        return 16
    if len(content) >= 80:
        return 10
    if content:
        return 4
    return 0


def _engagement_score(view_count: int, like_count: int) -> int:
    view = int(view_count or 0)
    like = int(like_count or 0)
    if view >= 100_000:
        score = _ENGAGE_MAX
    elif view >= 10_000:
        score = 16
    elif view >= 1_000:
        score = 10
    elif view >= 100:
        score = 5
    elif view > 0:
        score = 3
    else:
        score = 0
    # 高赞低播（垂直优质内容）小加分
    if like >= 500 and view < 100_000:
        score += 2
    return min(score, _ENGAGE_MAX)


def score_experience_item(
    *,
    title: str,
    content: str = "",
    source_platform: str = "bilibili",
    source_url: str = "",
    external_view_count: int = 0,
    external_like_count: int = 0,
    is_promotion: bool = False,
) -> tuple[int, str]:
    """综合评分一条经验贴，返回 (quality_score 0-100, grade A/B/C/D)。

    五维：来源可信度 30 + 内容完整度 30 + 互动信号 20 + 可溯源 10 +
    反软广 10。软广经验贴标注（is_promotion=True）→ 反软广维度为 0，
    拉低质量分（前端降权展示），但不至于打 D 级剔除。
    """
    trust = _trust_score(source_url, source_platform)
    completeness = _completeness_score(content)
    engagement = _engagement_score(external_view_count, external_like_count)
    traceable = _TRACEABLE if source_url.startswith(("http://", "https://")) else 0
    anti_promo = _ANTI_PROMO if not is_promotion else 0

    score = trust + completeness + engagement + traceable + anti_promo
    score = max(0, min(100, score))
    return score, grade_of(score)
