"""资讯质量分级 — 信源权威度 × 时效性 × 内容完整度 → 0-100 分 + A/B/C/D 级。

用于入库前过滤低质资讯、审核队列排序、前端质量徽章展示。
维度（外部调研结论）：
1. 信源权威度：edu.cn/gov.cn 官方 > 门户教育频道/官方媒体 > 培训机构/社区 > 其他
2. 时效性：考研资讯价值随时间衰减（报名/调剂窗口过期即失效）
3. 内容完整度：有正文（content）优于只有标题/摘要
4. 可溯源：source_url 有效才计分
"""
from datetime import datetime, timezone
from urllib.parse import urlparse

# 官方域名（含子域）
_OFFICIAL_SUFFIXES = (".edu.cn", ".gov.cn", ".ac.cn")
# 门户教育频道 / 官方媒体（信息差价值高的聚合源）
_PORTAL_DOMAINS = {
    "sina.com.cn",
    "sina.cn",
    "eol.cn",
    "sohu.com",
    "163.com",
    "qq.com",
    "people.com.cn",
    "xinhuanet.com",
    "chinanews.com",
    "huqiu.com",
}
# 培训机构 / 社区平台（有一定专业度但权威性弱）
_COMMUNITY_DOMAINS = {
    "offcn.com",
    "huatu.com",
    "fenbi.com",
    "mofangge.com",
    "gaokao.cn",
    "zhihu.com",
    "bilibili.com",
}

# 权威度分（总分 40）
_AUTHORITY_OFFICIAL = 40
_AUTHORITY_PORTAL = 25
_AUTHORITY_COMMUNITY = 15
_AUTHORITY_OTHER = 10
# 时效分（总分 30）
_FRESHNESS_MAX = 30
# 完整度分（总分 20）
_COMPLETENESS_MAX = 20
# 可溯源源（总分 10）
_TRACEABLE = 10

# 分级阈值（score >= 75 → A，>= 55 → B，>= 35 → C，其余 D）
GRADE_A = 75
GRADE_B = 55
GRADE_C = 35

_GRADES = ((GRADE_A, "A"), (GRADE_B, "B"), (GRADE_C, "C"))


def _authority_score(source_url: str) -> int:
    """按来源域名分级权威度。"""
    hostname = (urlparse(source_url or "").hostname or "").lower()
    if not hostname:
        return 0
    if any(hostname.endswith(s) for s in _OFFICIAL_SUFFIXES):
        return _AUTHORITY_OFFICIAL
    if any(hostname == d or hostname.endswith("." + d) for d in _PORTAL_DOMAINS):
        return _AUTHORITY_PORTAL
    if any(hostname == d or hostname.endswith("." + d) for d in _COMMUNITY_DOMAINS):
        return _AUTHORITY_COMMUNITY
    return _AUTHORITY_OTHER


def _freshness_score(published_at: datetime | None, crawled_at: datetime | None) -> int:
    """时效评分：24h 内满分，随天数衰减；未知发布时间给中性保守分。"""
    ts = published_at or crawled_at
    if not ts:
        return 0
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    hours = (datetime.now(timezone.utc) - ts).total_seconds() / 3600
    if hours < 24:
        return _FRESHNESS_MAX
    if hours < 7 * 24:
        return 25
    if hours < 30 * 24:
        return 18
    if hours < 90 * 24:
        return 10
    if hours < 180 * 24:
        return 5
    return 0


def _completeness_score(content: str, summary: str) -> int:
    """内容完整度：正文长度为主，有摘要加分。"""
    content = content or ""
    summary = summary or ""
    if len(content) >= 1000:
        base = _COMPLETENESS_MAX
    elif len(content) >= 500:
        base = 15
    elif len(content) >= 100:
        base = 10
    elif content:
        base = 5
    else:
        base = 0
    if summary and base < _COMPLETENESS_MAX:
        base += 2
    return min(base, _COMPLETENESS_MAX)


def grade_of(score: int) -> str:
    """score -> A/B/C/D。"""
    for threshold, grade in _GRADES:
        if score >= threshold:
            return grade
    return "D"


def _authority_reason(points: int) -> str:
    """信源权威度的逐级说明（可解释徽章用，Phase I）。"""
    if points >= _AUTHORITY_OFFICIAL:
        return "官方来源（edu.cn/gov.cn/ac.cn）"
    if points >= _AUTHORITY_PORTAL:
        return "门户/官方媒体（sina/eol/sohu 等）"
    if points >= _AUTHORITY_COMMUNITY:
        return "社区/培训机构（zhihu/bilibili/offcn 等）"
    if points > 0:
        return "普通站点"
    return "无来源链接"


def _freshness_reason(
    published_at: datetime | None, crawled_at: datetime | None
) -> str:
    """时效性说明（发布时间未知/衰减档位）。"""
    ts = published_at or crawled_at
    if not ts:
        return "发布时间未知"
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    hours = (datetime.now(timezone.utc) - ts).total_seconds() / 3600
    if hours < 24:
        return "发布 24 小时内"
    if hours < 7 * 24:
        return "发布一周内"
    if hours < 30 * 24:
        return "发布一个月内"
    if hours < 90 * 24:
        return "发布三个月内"
    if hours < 180 * 24:
        return "发布半年内"
    return "发布超过半年"


def score_item_detailed(
    *,
    title: str,
    content: str = "",
    summary: str = "",
    source_url: str = "",
    published_at: datetime | None = None,
    crawled_at: datetime | None = None,
) -> dict:
    """综合评分一条资讯并给出可解释明细（Phase I）。

    Returns:
        {"score": 0-100, "grade": A/B/C/D,
         "dimensions": [{"name","label","max","points","reason"}],
         "reasons": [str]} —— reasons 为未拿满维度的扣分说明，供质量徽章 hover。
    """
    authority = _authority_score(source_url)
    freshness = _freshness_score(published_at, crawled_at)
    completeness = _completeness_score(content, summary)
    traceable = _TRACEABLE if source_url.startswith(("http://", "https://")) else 0

    score = authority + freshness + completeness + traceable
    score = max(0, min(100, score))

    completeness_detail = (
        f"正文约 {len(content or '')} 字" if content else "无正文"
    )
    if summary and completeness < _COMPLETENESS_MAX:
        completeness_detail += "，有摘要加分"

    dimensions = [
        {
            "name": "authority",
            "label": "信源权威度",
            "max": _AUTHORITY_OFFICIAL,
            "points": authority,
            "reason": _authority_reason(authority),
        },
        {
            "name": "freshness",
            "label": "时效性",
            "max": _FRESHNESS_MAX,
            "points": freshness,
            "reason": _freshness_reason(published_at, crawled_at),
        },
        {
            "name": "completeness",
            "label": "内容完整度",
            "max": _COMPLETENESS_MAX,
            "points": completeness,
            "reason": completeness_detail,
        },
        {
            "name": "traceable",
            "label": "可溯源",
            "max": _TRACEABLE,
            "points": traceable,
            "reason": "无原文链接，不可溯源",
        },
    ]

    reasons = [
        f"{d['label']} {d['points']}/{d['max']}：{d['reason']}"
        for d in dimensions
        if d["points"] < d["max"]
    ]
    return {
        "score": score,
        "grade": grade_of(score),
        "dimensions": dimensions,
        "reasons": reasons,
    }


def score_item(
    *,
    title: str,
    content: str = "",
    summary: str = "",
    source_url: str = "",
    published_at: datetime | None = None,
    crawled_at: datetime | None = None,
) -> tuple[int, str]:
    """综合评分一条资讯，返回 (quality_score 0-100, grade A/B/C/D)。

    规则纯本地计算（零 LLM 成本），入库前/审核时调用。
    可解释明细见 score_item_detailed（Phase I）。
    """
    detailed = score_item_detailed(
        title=title,
        content=content,
        summary=summary,
        source_url=source_url,
        published_at=published_at,
        crawled_at=crawled_at,
    )
    return detailed["score"], detailed["grade"]
