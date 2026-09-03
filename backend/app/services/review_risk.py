"""审核队列风险排序 — 红/黄/绿让管理员只优先审可疑条目（M2+S3）。

第一性原理：人工审核是稀缺资源，平铺按时间排序会让真正危险的内容
（离题/软广/低质）淹没在正常条目里。本模块把既有纯规则信号
（主题门禁/软广检测/质量分/来源可信度/爬虫信誉）合成一个可解释的风险档位，
供 /api/admin/research-queue/pending 列表时现算排序——**不落库、不改持久化
quality_score、不改自动审门槛**（09-02 拍板：队列内信号，零迁移可回滚）。

档位判定（可解释优先，避免玄学权重）：
  high   主题离题命中强锚点 / 软广置信 ≥0.7 / 质量分 <35
  medium 主题无领域信号（存疑，正是 S2 需人工确认的口子）/
         软广置信 ≥0.4 / 来源 model_inferred 且爬虫无信誉历史
  low    以上皆无
risk_score 仅用于同档内细分排序：high 信号 +40 / medium +18 / low +5，封顶 100。
"""

import logging

from app.crawlers.research.experience_quality import detect_promotion, score_experience_item_detailed
from app.crawlers.research.quality import score_item_detailed
from app.crawlers.research.transformer import classify_topic_relevance
from app.models.ingestion import ExternalResearchItem

logger = logging.getLogger(__name__)

# 风险档位 → 排序权重（越大越靠前）
RISK_ORDER = {"high": 3, "medium": 2, "low": 1}

_HIGH_PENALTY = 40
_MEDIUM_PENALTY = 18
_LOW_PENALTY = 5

# 软广置信阈值：≥0.7 高危（多营销词叠加/无证据抬分），≥0.4 存疑
_PROMO_HIGH = 0.7
_PROMO_MEDIUM = 0.4
# 质量分低于入库红线（research_ingestion.QUALITY_MIN_SCORE 同值）→ 高危
_QUALITY_LOW = 35


def _quality_score(ext: ExternalResearchItem) -> int:
    """与 auto_review._score 同源的规则评分（新闻/经验各用其打分器）。"""
    meta = ext.external_meta or {}
    if ext.item_type == "experience_post":
        tags = [t for t in (meta.get("tags") or []) if isinstance(t, str)]
        is_promotion, _conf, promo_reason = detect_promotion(ext.title or "", ext.content or "", tags)
        detail = score_experience_item_detailed(
            title=ext.title or "",
            content=ext.content or "",
            source_platform=ext.source_platform or "user",
            source_url=ext.source_url or "",
            external_view_count=int(meta.get("view_count") or 0),
            external_like_count=int(meta.get("like_count") or 0),
            is_promotion=is_promotion,
            promotion_reason=promo_reason,
        )
    else:
        detail = score_item_detailed(
            title=ext.title or "",
            content=ext.content or "",
            summary=meta.get("summary") or "",
            source_url=ext.source_url or "",
        )
    return int(detail["score"])


def compute_review_risk(
    ext: ExternalResearchItem,
    reputation: dict[str, dict] | None = None,
) -> tuple[str, int, list[str]]:
    """计算单条待审条目的风险。

    Args:
        ext: 待审外部条目（JOIN 队列后带出）。
        reputation: source_reputation(db) 的爬虫信誉画像，可选（省 DB 查询时 None）。

    Returns:
        (risk_grade, risk_score, reasons)
        risk_grade ∈ {"high", "medium", "low"}；risk_score 0-100 同档细分排序用；
        reasons 为面向管理员的简明中文理由（可能为空 = 无异常信号）。
    """
    signals: list[tuple[str, str]] = []  # (level, reason)

    # 信号 1（S3 核心）：主题相关度三态 → True 高危 / None 存疑 / False 正常
    is_off, reason, _domain = classify_topic_relevance(ext.title or "", ext.content or "")
    if is_off is True:
        signals.append(("high", f"主题离题（{reason}）"))
    elif is_off is None:
        signals.append(("medium", "无领域信号待人工确认"))

    # 信号 2：软广/引流
    meta = ext.external_meta or {}
    tags = [t for t in (meta.get("tags") or []) if isinstance(t, str)]
    is_promotion, promo_conf, promo_reason = detect_promotion(
        ext.title or "", ext.content or "", tags
    )
    if is_promotion and promo_conf >= _PROMO_HIGH:
        signals.append(("high", f"疑似软广（置信 {promo_conf:.0%}）：{promo_reason}"))
    elif is_promotion and promo_conf >= _PROMO_MEDIUM:
        signals.append(("medium", f"疑似软广（置信 {promo_conf:.0%}）：{promo_reason}"))

    # 信号 3：规则质量分过低
    try:
        quality = _quality_score(ext)
    except Exception:
        logger.debug("review_risk: 打分失败 ext_id=%s", ext.id)
        quality = -1
    if quality >= 0 and quality < _QUALITY_LOW:
        signals.append(("high", f"质量分过低（{quality}/100，低于入库线 {_QUALITY_LOW}）"))

    # 信号 4：来源可信度 + 爬虫信誉（弱信号，只贡献 medium/low）
    credibility = ext.credibility or ""
    rep = (reputation or {}).get(ext.crawler_name or "")
    if credibility == "model_inferred" and rep is not None and rep.get("total", 0) == 0:
        signals.append(("medium", "来源为 AI 推断且该爬虫无审核历史"))
    elif rep is not None and rep.get("total", 0) >= 10 and rep.get("pass_rate", 1.0) < 0.7:
        signals.append(("medium", f"来源爬虫历史通过率低（{rep['pass_rate']:.0%}）"))
    if credibility == "official_verified":
        signals.append(("low", "官方来源（edu.cn/gov.cn）"))

    if not signals:
        return "low", 0, []

    grade = max((level for level, _ in signals), key=lambda lv: RISK_ORDER[lv])
    score = min(
        100,
        sum(
            _HIGH_PENALTY if lv == "high" else _MEDIUM_PENALTY if lv == "medium" else _LOW_PENALTY
            for lv, _ in signals
        ),
    )
    return grade, score, [reason for _, reason in signals]
