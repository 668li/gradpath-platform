"""外部调研统一入库服务 — 落盘爬虫改入库（系统设计主线 c / F9）。

3 个落盘爬虫（bilibili_research / web_article_research / rss_news_research）
共用本服务：写入 t_external_research_item + t_review_queue_item，
同时由各爬虫 store() 维护 crawler_runs 运行统计。
"""

import logging
from datetime import datetime
from hashlib import sha256
from typing import Any
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.crawlers.research.dedup import compute_simhash, find_similar, normalize_url
from app.models.ingestion import ExternalResearchItem, ReviewQueueItem
from app.models.kaoyan_news import KaoyanNews

logger = logging.getLogger(__name__)

# 直接映射到 ExternalResearchItem 核心列的字段；其余 parse 产物进 external_meta（来源元数据 F11）
_CORE_FIELDS = {"title", "content", "source_url", "source_platform"}

# 质量下限（D 级拒收）：kaoyan_news 入库前质量过滤阈值。
# transform_rss 已注入 quality_score（规则计算），低于该值直接不占审核队列。
QUALITY_MIN_SCORE = 35

# credibility 分级规则（P2）：官方域名 → official_verified；社区平台 → user_reported；其余 → model_inferred
# 合规红线（2026-09-06 对抗审计 F2）：yz.chsi.com.cn 是禁入站，绝不允许出现在信任域名表。
_OFFICIAL_DOMAINS = ("edu.cn", "gov.cn")
_COMMUNITY_PLATFORMS = {"bilibili", "v2ex", "github", "zhihu", "tieba"}

# 研招网红线：不入库、不分发（入库唯一咽喉写入即拒，可审计计数；promote 层复用做纵深）。
_REDLINE_HOSTS = ("yz.chsi.com.cn",)


def is_redline_url(source_url: str) -> bool:
    """URL 主机是否落在红线域名（含子域）。入库咽喉 + promote 纵深共用。"""
    hostname = (urlparse(source_url).hostname or "").lower()
    return any(hostname == h or hostname.endswith("." + h) for h in _REDLINE_HOSTS)


def _infer_credibility(source_url: str, source_platform: str) -> str:
    """按来源规则分级可信度，替代硬编码 model_inferred。

    规则（合规红线：外部数据须来源标注）：
    - 官方域名（edu.cn / gov.cn，含子域）→ official_verified
    - 社区平台（bilibili / v2ex / github / zhihu / tieba，平台名或 URL 域名命中）→ user_reported
    - 其余 → model_inferred（默认，需人工/模型核验后才可信任）
    """
    hostname = (urlparse(source_url).hostname or "").lower()
    if any(hostname == d or hostname.endswith("." + d) for d in _OFFICIAL_DOMAINS):
        return "official_verified"
    platform = source_platform.lower()
    if platform in _COMMUNITY_PLATFORMS or any(p in hostname for p in _COMMUNITY_PLATFORMS):
        return "user_reported"
    return "model_inferred"


def _normalize_biz_req_no(crawler_name: str, source_url: str) -> str:
    """生成审核队列幂等键：research:{crawler_name}:{sha256(source_url)[:12]}。

    同 URL 幂等：重复写入同一 URL 时 biz_req_no 相同，
    uk_review_queue_item_biz_req_no 唯一索引兜底。
    """
    digest = sha256(source_url.encode("utf-8")).hexdigest()[:12]
    return f"research:{crawler_name}:{digest}"


def _json_safe(value: Any) -> Any:
    """external_meta 写入 JSONB 列前保证 JSON 可序列化。

    parse 产物（如 transform_rss）可能携带 datetime 等非 JSON 原生类型，
    SQLite/Postgres JSONB 均不接受 → 统一转 isoformat 字符串。
    """
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    return value


def _load_kaoyan_dedup_baseline(db: Session) -> tuple[list[int], set[str]]:
    """加载库内已收录考研资讯的提纯基线（SimHash + 归一化 URL）。

    纳入范围（与库内已有条目比对，杜绝相似重复，Phase A5）：
    - KaoyanNews.status == 'approved'（已上线正文）的 title+summary
    - ExternalResearchItem.item_type == 'kaoyan_news'（含待审队列）的 title
    - 两类来源的 source_url（normalize_url 归一化后）

    仅 kaoyan_news 类型调用；其他类型继续走精确 URL 幂等。
    """
    hashes: list[int] = []
    norm_urls: set[str] = set()

    for row in (
        db.query(KaoyanNews.title, KaoyanNews.summary).filter(KaoyanNews.status == "approved").all()
    ):
        text = f"{row[0] or ''} {row[1] or ''}".strip()
        if text:
            hashes.append(compute_simhash(text))

    for row in (
        db.query(ExternalResearchItem.title)
        .filter(ExternalResearchItem.item_type == "kaoyan_news")
        .all()
    ):
        if row[0]:
            hashes.append(compute_simhash(row[0]))

    for row in db.query(KaoyanNews.source_url).all():
        norm_urls.add(normalize_url(row[0]))
    for row in (
        db.query(ExternalResearchItem.source_url)
        .filter(ExternalResearchItem.item_type == "kaoyan_news")
        .all()
    ):
        norm_urls.add(normalize_url(row[0]))

    return hashes, norm_urls


def store_research_items(
    db: Session,
    *,
    crawler_name: str,
    item_type: str,  # experience_post / dark_knowledge / kaoyan_news
    items: list[dict],  # 爬虫 parse 产物
    source_platform: str,  # bilibili / web / rss
    run_id: str,  # CrawlerRun.id (UUID hex)
) -> dict:
    """落盘爬虫改入库：写入 t_external_research_item + t_review_queue_item。

    - 幂等：source_url 唯一索引去重（uk_external_research_item_source_url）
      + 审核队列 biz_req_no 唯一（uk_review_queue_item_biz_req_no）
    - 每条：ExternalResearchItem(review_status='PENDING')
      + ReviewQueueItem(item_type='external_research', review_status='PENDING')
    - biz_req_no = f"research:{crawler_name}:{md5(source_url)[:12]}"，同 URL 幂等
    - 全程一个事务；异常 rollback 并如实抛出
    - 依赖注入 db（Session），不自行创建 session

    Args:
        db: 数据库会话（依赖注入，不自行创建）
        crawler_name: 爬虫名称（对应 crawler_runs.source_name）
        item_type: 条目类型枚举
        items: 爬虫 parse 产物列表，至少含 title/content/source_url
        source_platform: 来源平台
        run_id: CrawlerRun.id（UUID 字符串）

    Returns:
        {"inserted": int, "duplicated": int, "redline_rejected": int}
    """
    inserted = 0
    duplicated = 0
    redline_rejected = 0
    try:
        # 提纯基线：仅 kaoyan_news 启用（库内已收录条目的 simhash + 归一化 URL，批次内增量比对）
        kaoyan_hashes: list[int] = []
        kaoyan_norm_urls: set[str] = set()
        if item_type == "kaoyan_news":
            kaoyan_hashes, kaoyan_norm_urls = _load_kaoyan_dedup_baseline(db)

        for item in items:
            source_url = (item.get("source_url") or "").strip()
            if not source_url:
                logger.debug("[research_ingestion] 跳过无 source_url 的条目")
                continue
            if len(source_url) > 500:
                source_url = source_url[:500]
                logger.warning("[research_ingestion] source_url 超长已截断: %s...", source_url[:50])

            # 合规红线：研招网(chsi)禁入，入库唯一咽喉即拒（对抗审计 F2 修法②）
            if is_redline_url(source_url):
                redline_rejected += 1
                logger.warning(
                    "[research_ingestion] 研招网红线拒收（不落库）: %s (crawler=%s)",
                    source_url[:80],
                    crawler_name,
                )
                continue

            # 幂等去重：source_url 已存在 → duplicated+1 跳过
            existing = (
                db.query(ExternalResearchItem)
                .filter(ExternalResearchItem.source_url == source_url)
                .first()
            )
            if existing:
                duplicated += 1
                continue

            title = (item.get("title") or "")[:300]
            content = item.get("content") or ""

            # === 提纯去重（Phase A5：先提纯再入库）===
            # kaoyan_news 信息差管线：与库内已收录条目比对——
            # 归一化 URL 命中 / simhash 相似 → 拒收（duplicated+1）；
            # quality_score < QUALITY_MIN_SCORE（D 级）→ 直接不占审核队列。
            if item_type == "kaoyan_news":
                norm_url = normalize_url(source_url)
                if norm_url in kaoyan_norm_urls:
                    logger.info(
                        "[research_ingestion] kaoyan_news 归一化 URL 重复拒收: %s", norm_url
                    )
                    duplicated += 1
                    continue
                sim_text = f"{title} {content[:500]}".strip()
                if sim_text and find_similar(sim_text, kaoyan_hashes) is not None:
                    logger.info("[research_ingestion] kaoyan_news simhash 相似拒收: %s", title[:40])
                    duplicated += 1
                    continue
                quality_score = item.get("quality_score")
                if (
                    isinstance(quality_score, (int, float))
                    and int(quality_score) < QUALITY_MIN_SCORE
                ):
                    logger.info(
                        "[research_ingestion] kaoyan_news 质量分 %s < %s 拒收: %s",
                        int(quality_score),
                        QUALITY_MIN_SCORE,
                        title[:40],
                    )
                    continue
                # 批次内去重：本次已通过的新条目纳入 simhash 比对基线
                # （norm_url 不纳入基线：不同条目可能共享同一来源页 URL，
                #  归一化去重仅针对库内已收录条目，批次内由精确 URL 幂等兜底）
                if sim_text:
                    kaoyan_hashes.append(compute_simhash(sim_text))

            # 除核心列外的 parse 产物全部进 external_meta，保留行级来源元数据（F11）；
            # datetime 等非 JSON 原生类型先转 isoformat（JSONB 列要求）
            external_meta = _json_safe({k: v for k, v in item.items() if k not in _CORE_FIELDS})

            ext_item = ExternalResearchItem(
                crawler_name=crawler_name,
                crawler_run_id=run_id,
                item_type=item_type,
                title=title,
                content=content,
                source_url=source_url,
                source_platform=source_platform,
                external_meta=external_meta,
                credibility=_infer_credibility(source_url, source_platform),
                review_status="PENDING",
            )
            db.add(ext_item)
            db.flush()  # 取 ext_item.id 供审核队列引用，仍在同一事务内

            db.add(
                ReviewQueueItem(
                    item_type="external_research",
                    ref_item_id=ext_item.id,
                    source_url=source_url,
                    review_status="PENDING",
                    biz_req_no=_normalize_biz_req_no(crawler_name, source_url),
                )
            )
            inserted += 1

        db.commit()
        return {
            "inserted": inserted,
            "duplicated": duplicated,
            "redline_rejected": redline_rejected,
        }
    except Exception:
        db.rollback()
        logger.exception("[research_ingestion] 入库失败，已回滚")
        raise
