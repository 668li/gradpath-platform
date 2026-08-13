"""外部调研统一入库服务 — 落盘爬虫改入库（系统设计主线 c / F9）。

3 个落盘爬虫（bilibili_research / web_article_research / rss_news_research）
共用本服务：写入 t_external_research_item + t_review_queue_item，
同时由各爬虫 store() 维护 crawler_runs 运行统计。
"""
import logging
from hashlib import md5
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.models.ingestion import ExternalResearchItem, ReviewQueueItem

logger = logging.getLogger(__name__)

# 直接映射到 ExternalResearchItem 核心列的字段；其余 parse 产物进 external_meta（来源元数据 F11）
_CORE_FIELDS = {"title", "content", "source_url", "source_platform"}

# credibility 分级规则（P2）：官方域名 → official_verified；社区平台 → user_reported；其余 → model_inferred
_OFFICIAL_DOMAINS = ("edu.cn", "yz.chsi.com.cn", "gov.cn")
_COMMUNITY_PLATFORMS = {"bilibili", "v2ex", "github", "zhihu"}


def _infer_credibility(source_url: str, source_platform: str) -> str:
    """按来源规则分级可信度，替代硬编码 model_inferred。

    规则（合规红线：外部数据须来源标注）：
    - 官方域名（edu.cn / yz.chsi.com.cn / gov.cn，含子域）→ official_verified
    - 社区平台（bilibili / v2ex / github / zhihu，平台名或 URL 域名命中）→ user_reported
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
    """生成审核队列幂等键：research:{crawler_name}:{md5(source_url)[:12]}。

    同 URL 幂等：重复写入同一 URL 时 biz_req_no 相同，
    uk_review_queue_item_biz_req_no 唯一索引兜底。
    """
    digest = md5(source_url.encode("utf-8")).hexdigest()[:12]
    return f"research:{crawler_name}:{digest}"


def store_research_items(
    db: Session,
    *,
    crawler_name: str,
    item_type: str,           # experience_post / dark_knowledge / kaoyan_news
    items: list[dict],        # 爬虫 parse 产物
    source_platform: str,     # bilibili / web / rss
    run_id: str,              # CrawlerRun.id (UUID hex)
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
        {"inserted": int, "duplicated": int}
    """
    inserted = 0
    duplicated = 0
    try:
        for item in items:
            source_url = (item.get("source_url") or "").strip()
            if not source_url:
                logger.debug("[research_ingestion] 跳过无 source_url 的条目")
                continue
            if len(source_url) > 500:
                source_url = source_url[:500]
                logger.warning("[research_ingestion] source_url 超长已截断: %s...", source_url[:50])

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
            # 除核心列外的 parse 产物全部进 external_meta，保留行级来源元数据（F11）
            external_meta = {k: v for k, v in item.items() if k not in _CORE_FIELDS}

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
        return {"inserted": inserted, "duplicated": duplicated}
    except Exception:
        db.rollback()
        logger.exception("[research_ingestion] 入库失败，已回滚")
        raise
