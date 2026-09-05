"""审核队列消费服务 — 审核通过后把 t_external_research_item 落业务表。

审核链路统一走新队列（t_review_queue_item）后的唯一消费端（P1 修理）：
- approve → research_promote.promote_external_item() 落业务表
- 按 item_type 分派：experience_post → ExperiencePost / kaoyan_news → KaoyanNews
  / dark_knowledge → DarkKnowledge（防御分支，当前无爬虫写入该类型）
- status=approved；按 source_url 幂等去重（已存在则跳过）
- 复用 ResearchTransformer 的清洗/标签/分类逻辑，与旧 import_* 行为等价

事务约定：本服务只做 db.add / 属性回填，不 commit / 不回滚，
由调用方（API 端点或 auto_approve）统一提交，保证"队列状态 + 业务数据"原子。
"""

import logging
import re
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.utils.business_time import beijing_today
from app.crawlers.research.experience_quality import (
    detect_promotion,
    extract_experience_meta_with_evidence,
    score_experience_item_detailed,
)
from app.crawlers.research.news_meta import extract_news_structured_meta_with_evidence
from app.crawlers.research.quality import score_item_detailed
from app.crawlers.research.transformer import (
    OFF_TOPIC_REJECT_KEYWORDS,
    SYSTEM_USER_ID,
    ResearchTransformer,
    classify_topic_relevance,
)
from app.models.experience_post import ExperiencePost
from app.models.ingestion import DataSourceMeta, ExternalResearchItem
from app.models.kaoyan_news import KaoyanNews
from app.models.user import User

logger = logging.getLogger(__name__)

# data_freshness 渠道别名（app/api/data_freshness.py SOURCES 键）；确认入库时回写新鲜度。
# 优先级：external_meta.source_channel（unified 聚合包直接带 offcn/sina_edu 等渠道名）
# > crawler_name 别名映射（通用网页/院校内容归入 kaoyan 渠道）。
_FRESHNESS_SOURCE_ALIASES = {
    "web_article_research": "kaoyan",
    "real_data": "kaoyan",
    "bilibili_research": "kaoyan",
}

# ----------------------------------------------------------------------
# 关键时间点规则抽取（Phase C1 同步兜底；LLM 增强见 news_enhance.py）
# 覆盖信息差核心窗口：报名 / 网上确认 / 截止 / 初试 / 复试 / 调剂
# ----------------------------------------------------------------------
# 中文日期模式：20xx年X月X日 或 X月X日（"日"字可选，支持 1-2 位月日）
_CHINESE_DATE = r"(?:20\d{2}年)?(?:1[0-2]|0?[1-9])月(?:3[01]|[12]\d|0?[1-9])日?"
# 标签 → 日期：标签后 15 字符内出现日期（非贪婪，避免跨句误配）
_LABEL_DATE_RE = re.compile(
    r"(?P<label>网上确认|报名|截止|初试|复试|调剂|确认)"
    r"[^。；\n]{0,15}?"
    r"(?P<date>" + _CHINESE_DATE + r")"
)
# 日期区间：X月X日 至/—/~/到 X月X日（报名窗口、调剂系统开放期等）
_RANGE_RE = re.compile(
    r"(?P<date1>" + _CHINESE_DATE + r")\s*(?:至|—|–|-|~|到)\s*(?P<date2>" + _CHINESE_DATE + r")"
)


# 无年份日期按"最近的该月日"推断年份（未来优先）：10 月报名/12 月初试落在当年，
# 3-4 月复试/调剂落次年的场景可正确归属；规则版近似，LLM 增强版会精确化。
# 年份基准按北京日历（today 可注入供测试）。
def _resolve_year(month: int, day: int, today: date | None = None) -> int:
    today = today or beijing_today()
    year = today.year
    if date(year, month, day) < today:
        year += 1
    return year


def _parse_chinese_date(text: str, default_year: int | None = None) -> date | None:
    """解析 '2025年10月9日' / '10月9日' → date；格式不符返回 None。

    default_year：无显式年份时的年份兜底（区间第二个日期继承首日期年份用）。
    """
    m = re.match(r"(?:20\d{2}年)?(?:1[0-2]|0?[1-9])月(?:3[01]|[12]\d|0?[1-9])日?", text)
    if not m:
        return None
    token = m.group(0)
    year = None
    ym = re.match(r"(20\d{2})年", token)
    if ym:
        year = int(ym.group(1))
    md = re.search(r"(1[0-2]|0?[1-9])月(3[01]|[12]\d|0?[1-9])日?", token)
    if not md:
        return None
    month, day = int(md.group(1)), int(md.group(2))
    if month < 1 or month > 12 or day < 1 or day > 31:
        return None
    if year is None:
        year = default_year if default_year is not None else _resolve_year(month, day)
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _iso_date(d: date) -> str:
    return d.isoformat()


def extract_key_dates(title: str, content: str) -> list[dict]:
    """从标题+正文抽取关键时间点（规则版，同步零成本）。

    返回 [{label, date, end_date?}, ...]：date/end_date 为 ISO 日期字符串。
    同一 (label, date) 去重；区间优先（报名/调剂窗口含起止）。
    """
    text_ = f"{title or ''}\n{(content or '')[:3000]}"
    results: list[dict] = []

    def _add(label: str, d1: date, d2: date | None = None) -> None:
        item = {"label": label, "date": _iso_date(d1)}
        if d2:
            item["end_date"] = _iso_date(d2)
        if item not in results:
            results.append(item)

    # 1) 区间：先找日期范围（如"2025年10月9日至10月28日"）
    for m in _RANGE_RE.finditer(text_):
        d1 = _parse_chinese_date(m.group("date1"))
        # 区间第二个日期无显式年份时继承首日期年份（"10月15日至10月28日"同年）
        d2 = _parse_chinese_date(m.group("date2"), default_year=d1.year if d1 else None)
        if d1 and d2:
            # 尝试向前找标签（如"报名时间："）
            prefix = text_[max(0, m.start() - 12) : m.start()]
            label = None
            for cand in ("网上确认", "报名", "截止", "初试", "复试", "调剂", "确认"):
                if cand in prefix:
                    label = cand
                    break
            _add(label or "窗口", d1, d2)

    # 2) 标签→日期：单点关键时间（初试/复试/截止）
    for m in _LABEL_DATE_RE.finditer(text_):
        d = _parse_chinese_date(m.group("date"))
        if not d:
            continue
        label = m.group("label")
        if label == "确认" and "网上确认" in text_[max(0, m.start() - 6) : m.start() + 8]:
            label = "网上确认"
        # 区间已覆盖的日期不再重复（避免报名窗口拆成单点）
        if any(r["label"] == label and r["date"] == d.isoformat() for r in results):
            continue
        _add(label, d)

    return results


def _compute_is_expired(
    published_at: datetime | None,
    crawled_at: datetime | None,
    key_dates: list[dict],
) -> bool:
    """时效过期判定：有关键日期则全部已过 → 过期；否则按发布时间超 180 天。"""
    now = datetime.now(timezone.utc)
    dates: list[datetime] = []
    for kd in key_dates:
        for field in ("end_date", "date"):
            raw = kd.get(field)
            if not raw:
                continue
            try:
                d = datetime.fromisoformat(raw)
                if d.tzinfo is None:
                    d = d.replace(tzinfo=timezone.utc)
                dates.append(d)
            except ValueError:
                continue
    if dates:
        return all(d < now for d in dates)
    ts = published_at or crawled_at
    if not ts:
        return False
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return (now - ts).days > 180


def _ensure_system_user(db: Session) -> None:
    """确保 SYSTEM_USER_ID 用户存在（ExperiencePost.user_id 外键指向）。

    与旧链路 seed_from_research._ensure_system_user 等价；PG 启用外键时缺失会报错。
    """
    user = db.query(User).filter(User.id == SYSTEM_USER_ID).first()
    if not user:
        db.add(
            User(
                id=SYSTEM_USER_ID,
                email="system@gradpath.local",
                name="系统",
                password_hash="",
            )
        )


def _parse_dt(value: Any) -> datetime | None:
    """把 external_meta 里的时间（str / datetime / None）统一为 datetime。"""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
    return None


def _backfill_data_source(db: Session, ext_item: ExternalResearchItem, reviewer: str) -> None:
    """按 source_url 回填 t_data_source.review_status（匹配到才更新）。"""
    ds = db.query(DataSourceMeta).filter(DataSourceMeta.source_url == ext_item.source_url).first()
    if ds is not None and ds.review_status != "APPROVED":
        ds.review_status = "APPROVED"
        ds.reviewed_by = reviewer


def _touch_data_freshness(db: Session, ext_item: ExternalResearchItem) -> None:
    """审核 confirm 入库时回写 data_freshness 表（B4）。

    - 渠道匹配：external_meta.source_channel > crawler_name 别名映射
    - 无匹配渠道则跳过；表不存在（SQLite 未迁移场景）降级跳过，不阻塞审核
    - 只做 db.execute，不 commit（与调用方同一事务，保证原子）
    """
    meta = ext_item.external_meta or {}
    source_name = meta.get("source_channel") or _FRESHNESS_SOURCE_ALIASES.get(ext_item.crawler_name)
    if not source_name:
        return
    try:
        row = db.execute(
            text("SELECT records_count FROM data_freshness WHERE source_name=:n"),
            {"n": source_name},
        ).fetchone()
        if row is None:
            db.execute(
                text(
                    "INSERT INTO data_freshness "
                    "(source_name, last_successful_crawl, records_count, status, updated_at) "
                    "VALUES (:n, CURRENT_TIMESTAMP, 1, 'active', CURRENT_TIMESTAMP)"
                ),
                {"n": source_name},
            )
        else:
            db.execute(
                text(
                    "UPDATE data_freshness SET last_successful_crawl=CURRENT_TIMESTAMP, "
                    "records_count=records_count+1, status='active', "
                    "updated_at=CURRENT_TIMESTAMP WHERE source_name=:n"
                ),
                {"n": source_name},
            )
    except Exception:
        logger.warning(
            "[research_promote] 回写 data_freshness 失败（表不存在则跳过）: %s", source_name
        )


def _promote_experience_post(db: Session, ext_item: ExternalResearchItem, reviewer: str) -> dict:
    """落 ExperiencePost：复用 transform_bilibili 清洗，status=approved，source_url 幂等。

    Phase G 提纯：落库时注入质量分（打分器五维：来源可信度/完整度/互动/
    可溯源/反软广）、软广标注（detect_promotion，命中标注但不下架）、
    结构化元信息（extract_experience_meta：学科/阶段/院校/目标分/方法）。
    """
    # 幂等去重：业务表已存在同 URL → 跳过
    exists = (
        db.query(ExperiencePost.id).filter(ExperiencePost.source_url == ext_item.source_url).first()
    )
    if exists:
        logger.info("[research_promote] experience_post 已存在，跳过: %s", ext_item.source_url)
        return {"promoted": 0, "skipped": 1}

    meta = ext_item.external_meta or {}
    # 重组原始 item → 复用 transformer 清洗/标签/分类（与旧 import_bilibili_research 等价）
    raw = {
        **meta,
        "title": ext_item.title,
        "content": ext_item.content,
        "summary": (meta.get("summary") or ext_item.content)[:500],
        "source_url": ext_item.source_url,
        "source_platform": ext_item.source_platform,
    }
    payloads = ResearchTransformer.transform_bilibili([raw])

    if not payloads:
        # 回退：管理员已审核通过，质量过滤不应再丢弃（可能仅因过短/含引流词）
        payloads = [
            {
                "user_id": SYSTEM_USER_ID,
                "title": ext_item.title,
                "summary": (meta.get("summary") or ext_item.content)[:500],
                "content": ext_item.content,
                "tags": [t for t in (meta.get("tags") or []) if isinstance(t, str)],
                "category": ResearchTransformer._infer_category(ext_item.title),
                "source_platform": ext_item.source_platform,
                "source_url": ext_item.source_url,
                "external_view_count": int(meta.get("view_count") or 0),
                "external_like_count": int(meta.get("like_count") or 0),
                "status": "approved",
                "is_verified": False,
                "is_anonymous": False,
            }
        ]

    payload = payloads[0]
    payload["status"] = "approved"  # 管理员显式确认后落库

    # ---- Phase G 提纯注入（规则版，零 LLM 成本）----
    title = ext_item.title
    raw_content = ext_item.content or ""
    tags = [t for t in (payload.get("tags") or []) if isinstance(t, str)]

    # ---- 主题相关度硬门禁（S1）----
    # 管理员审核通过 ≠ 主题相关：免费/通用情绪词（心态/坚持）可能骗过人工审核。
    # 这里补一刀：命中离题黑名单 → 打 is_off_topic=True 仍落库（不删、可恢复），
    # 但 feed 查询显式排除；黑名单命中再额外把 category 规制为 off_topic。
    topic_off, topic_reason, topic_domain = classify_topic_relevance(
        title=title, content=raw_content, tags=tags
    )
    payload["is_off_topic"] = topic_off
    payload["topic_reason"] = topic_reason if topic_off else None
    payload["topic_domain"] = topic_domain
    if topic_off:
        logger.warning(
            "[research_promote] 主题离题仍需写入(打标不展示): %s（%s）", title[:40], topic_reason
        )
        # 强离题词命中 → 归类规范化 off_topic，聚合层同样不可见
        if any(kw.lower() in f"{title} {raw_content}".lower() for kw in OFF_TOPIC_REJECT_KEYWORDS):
            payload["category"] = "off_topic"

    # 1) 软广检测：命中标注但不下架（管理员已人工审核通过，前端知情降权）
    is_promotion, promo_conf, promo_reason = detect_promotion(title, raw_content, tags)

    # 2) 质量分（可解释，Phase I）：采集期 meta 已带则沿用分数，原因明细规则版
    #    重算（同一打分器输入一致，分数与采集期一致；reasons 供质量徽章 hover）
    score_detail = score_experience_item_detailed(
        title=title,
        content=raw_content,
        source_platform=ext_item.source_platform,
        source_url=ext_item.source_url,
        external_view_count=int(meta.get("view_count") or payload.get("external_view_count") or 0),
        external_like_count=int(meta.get("like_count") or payload.get("external_like_count") or 0),
        is_promotion=is_promotion,
        promotion_reason=promo_reason,
    )
    quality_score, quality_grade = meta.get("quality_score"), meta.get("quality_grade")
    if not isinstance(quality_score, (int, float)) or not isinstance(quality_grade, str):
        quality_score, quality_grade = score_detail["score"], score_detail["grade"]
    payload["quality_score"] = int(quality_score)
    payload["quality_grade"] = quality_grade
    payload["quality_reasons"] = score_detail["reasons"]

    # 3) 结构化元信息（决策数据卡）+ 证据链（Phase I）：学科/阶段/院校/目标分/方法，
    #    evidence=原文片段（≤40 字）、confidence=规则置信度（关键词 0.9/院校 0.85/分数 0.8）
    structured_meta, evidence, confidence = extract_experience_meta_with_evidence(
        title, raw_content, tags
    )
    payload["structured_meta"] = {
        **structured_meta,
        "evidence": evidence,
        "confidence": confidence,
    }
    payload["is_promotion"] = is_promotion
    payload["promotion_confidence"] = promo_conf
    payload["promotion_reason"] = promo_reason

    _ensure_system_user(db)
    db.add(ExperiencePost(**payload))
    _backfill_data_source(db, ext_item, reviewer)
    return {"promoted": 1, "skipped": 0}


def _promote_kaoyan_news(db: Session, ext_item: ExternalResearchItem, reviewer: str) -> dict:
    """落 KaoyanNews：status=approved，source_url 幂等。

    Phase C1 提纯：落库时补齐 quality_score/grade（采集期已算则沿用，
    缺失则规则版现场计算）、key_dates（规则正则抽取，LLM 增强见 news_enhance）、
    is_expired 时效标记，保证审核确认后前端拿到的是提纯后的结构化数据。
    """
    exists = db.query(KaoyanNews.id).filter(KaoyanNews.source_url == ext_item.source_url).first()
    if exists:
        logger.info("[research_promote] kaoyan_news 已存在，跳过: %s", ext_item.source_url)
        return {"promoted": 0, "skipped": 1}

    meta = ext_item.external_meta or {}
    crawled_at = _parse_dt(meta.get("crawled_at")) or datetime.now(timezone.utc)
    published_at = _parse_dt(meta.get("published_at"))
    summary = (meta.get("summary") or ext_item.content[:500]) or ""
    content = ext_item.content or ""

    # 质量分（可解释，Phase I）：采集期 transform_rss 已注入则沿用分数，
    # 原因明细规则版重算；缺失（老数据/兜底路径）现场规则计算
    score_detail = score_item_detailed(
        title=ext_item.title,
        content=content,
        summary=summary,
        source_url=ext_item.source_url,
        published_at=published_at,
        crawled_at=crawled_at,
    )
    quality_score, quality_grade = meta.get("quality_score"), meta.get("quality_grade")
    if not isinstance(quality_score, (int, float)) or not isinstance(quality_grade, str):
        quality_score, quality_grade = score_detail["score"], score_detail["grade"]
    quality_score = int(quality_score)

    # 关键时间点 + 时效标记（同步规则版，零成本兜底）
    key_dates = extract_key_dates(ext_item.title, content)
    is_expired = _compute_is_expired(published_at, crawled_at, key_dates)

    # 结构化元信息（决策数据卡：招生人数/考试科目/参考书）+ 证据链（Phase I）：
    # evidence=原文片段（≤40 字）、confidence=规则置信度、effective_year=数据年份
    # （如"2026 年招生计划"→ 2026，取不到为 None 前端诚实降级）
    structured_meta, evidence, confidence, effective_year = (
        extract_news_structured_meta_with_evidence(ext_item.title, content)
    )
    structured_meta = {
        **structured_meta,
        "evidence": evidence,
        "confidence": confidence,
        "effective_year": effective_year,
    }

    db.add(
        KaoyanNews(
            title=ext_item.title,
            summary=summary or None,
            content=content or None,
            source_platform=ext_item.source_platform,
            source_url=ext_item.source_url,
            published_at=published_at,
            crawled_at=crawled_at,
            status="approved",
            category=(meta.get("category") or "general"),
            tags=[t for t in (meta.get("tags") or []) if isinstance(t, str)],
            ai_summary=meta.get("ai_summary"),
            quality_score=quality_score,
            quality_grade=quality_grade,
            quality_reasons=score_detail["reasons"],
            key_dates=key_dates,
            is_expired=is_expired,
            structured_meta=structured_meta,
        )
    )
    _backfill_data_source(db, ext_item, reviewer)
    return {"promoted": 1, "skipped": 0}


def _promote_dark_knowledge(db: Session, ext_item: ExternalResearchItem, reviewer: str) -> dict:
    """落 DarkKnowledge（防御分支）— 当前无爬虫写入该类型，仅按 meta.stage 兜底。"""
    from app.models.grad_intel import DarkKnowledge

    meta = ext_item.external_meta or {}
    stage = meta.get("stage")
    if not stage:
        logger.warning(
            "[research_promote] dark_knowledge 缺 stage，跳过落库: %s", ext_item.source_url
        )
        return {"promoted": 0, "skipped": 1}
    exists = db.query(DarkKnowledge.id).filter(DarkKnowledge.title == ext_item.title).first()
    if exists:
        return {"promoted": 0, "skipped": 1}
    db.add(
        DarkKnowledge(
            stage=stage,
            category=(meta.get("category") or "general"),
            title=ext_item.title,
            content=ext_item.content,
            importance=(meta.get("importance") or "high"),
            common_misconception=meta.get("common_misconception"),
            actionable_advice=meta.get("actionable_advice"),
            verification_method=meta.get("verification_method"),
            tags=[t for t in (meta.get("tags") or []) if isinstance(t, str)],
            sort_order=int(meta.get("sort_order") or 0),
        )
    )
    _backfill_data_source(db, ext_item, reviewer)
    return {"promoted": 1, "skipped": 0}


def promote_external_item(db: Session, ext_item: ExternalResearchItem, reviewer: str) -> dict:
    """审核通过 → 落业务表（幂等）。返回 {"promoted": int, "skipped": int}。

    Args:
        db: 数据库会话（由调用方统一 commit）
        ext_item: t_external_research_item 条目（审核通过的对象）
        reviewer: 审核人标识（admin email）
    """
    dispatch = {
        "experience_post": _promote_experience_post,
        "kaoyan_news": _promote_kaoyan_news,
        "dark_knowledge": _promote_dark_knowledge,
    }
    handler = dispatch.get(ext_item.item_type)
    if handler is None:
        logger.warning(
            "[research_promote] 未知 item_type=%s，仅回填状态不落业务表",
            ext_item.item_type,
        )
        return {"promoted": 0, "skipped": 1}
    result = handler(db, ext_item, reviewer)
    if result.get("promoted", 0) > 0:
        # 确认入库成功 → 回写 data_freshness（同事务，由调用方统一 commit）
        _touch_data_freshness(db, ext_item)
        # Phase C2：kaoyan_news 落库后异步投递 LLM 增强（失败自动降级规则版）
        if ext_item.item_type == "kaoyan_news":
            try:
                from app.services.news_enhance import schedule_news_enhancement

                schedule_news_enhancement(limit=5)
            except Exception:  # noqa: BLE001 — 增强投递失败不影响审核主流程
                logger.warning("[research_promote] 投递资讯增强任务失败，已忽略")
    return result
