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
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.crawlers.research.transformer import ResearchTransformer, SYSTEM_USER_ID
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
    ds = (
        db.query(DataSourceMeta)
        .filter(DataSourceMeta.source_url == ext_item.source_url)
        .first()
    )
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
    source_name = meta.get("source_channel") or _FRESHNESS_SOURCE_ALIASES.get(
        ext_item.crawler_name
    )
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


def _promote_experience_post(
    db: Session, ext_item: ExternalResearchItem, reviewer: str
) -> dict:
    """落 ExperiencePost：复用 transform_bilibili 清洗，status=approved，source_url 幂等。"""
    # 幂等去重：业务表已存在同 URL → 跳过
    exists = (
        db.query(ExperiencePost.id)
        .filter(ExperiencePost.source_url == ext_item.source_url)
        .first()
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
    _ensure_system_user(db)
    db.add(ExperiencePost(**payload))
    _backfill_data_source(db, ext_item, reviewer)
    return {"promoted": 1, "skipped": 0}


def _promote_kaoyan_news(
    db: Session, ext_item: ExternalResearchItem, reviewer: str
) -> dict:
    """落 KaoyanNews：status=approved，source_url 幂等。"""
    exists = (
        db.query(KaoyanNews.id)
        .filter(KaoyanNews.source_url == ext_item.source_url)
        .first()
    )
    if exists:
        logger.info("[research_promote] kaoyan_news 已存在，跳过: %s", ext_item.source_url)
        return {"promoted": 0, "skipped": 1}

    meta = ext_item.external_meta or {}
    crawled_at = _parse_dt(meta.get("crawled_at")) or datetime.now(timezone.utc)
    db.add(
        KaoyanNews(
            title=ext_item.title,
            summary=(meta.get("summary") or ext_item.content[:500]),
            content=ext_item.content,
            source_platform=ext_item.source_platform,
            source_url=ext_item.source_url,
            published_at=_parse_dt(meta.get("published_at")),
            crawled_at=crawled_at,
            status="approved",
            category=(meta.get("category") or "general"),
            tags=[t for t in (meta.get("tags") or []) if isinstance(t, str)],
        )
    )
    _backfill_data_source(db, ext_item, reviewer)
    return {"promoted": 1, "skipped": 0}


def _promote_dark_knowledge(
    db: Session, ext_item: ExternalResearchItem, reviewer: str
) -> dict:
    """落 DarkKnowledge（防御分支）— 当前无爬虫写入该类型，仅按 meta.stage 兜底。"""
    from app.models.grad_intel import DarkKnowledge

    meta = ext_item.external_meta or {}
    stage = meta.get("stage")
    if not stage:
        logger.warning(
            "[research_promote] dark_knowledge 缺 stage，跳过落库: %s", ext_item.source_url
        )
        return {"promoted": 0, "skipped": 1}
    exists = (
        db.query(DarkKnowledge.id)
        .filter(DarkKnowledge.title == ext_item.title)
        .first()
    )
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


def promote_external_item(
    db: Session, ext_item: ExternalResearchItem, reviewer: str
) -> dict:
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
    return result
