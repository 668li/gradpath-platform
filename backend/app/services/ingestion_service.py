"""外部数据入库服务 — 来源标注 CRUD + 人工触发 + 人工确认入库（合规红线）。

合规红线（不批量抓取研招网 / 仅人工确认入库 / 外部数据来源标注）：
- ``trigger_ingest``：人工触发已注册爬虫（研招网 real_data 等）。护栏配置强制带上限
  （max_pages/max_items/rate_limit），产物一律经 store_research_items 进 PENDING
  审核队列，不自动落业务表。
- ``confirm_ingest``：管理员人工确认 → 写 ``confirmed_fields`` + ``source_url``
  来源追溯，经 research_promote 落业务表（ExperiencePost / KaoyanNews），
  按 source_url 幂等去重；同时回填 t_data_source 来源标注。
- ``list_sources`` / ``update_source``：t_data_source 来源与可信度管理。

与 research_queue（/api/admin/research-queue）的审核链路共用 promote 服务，
本服务是 /api/admin/research 契约端点（方案 C 落地）的实现层。
"""

import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.crawlers.crawler_config import load_config
from app.crawlers.registry import get_crawler
from app.models.crawler_run import CrawlerRun
from app.models.ingestion import DataSourceMeta, ExternalResearchItem, ReviewQueueItem
from app.services.research_promote import promote_external_item

logger = logging.getLogger(__name__)


class IngestionConflictError(ValueError):
    """409 语义：记录已审核 / 来源 URL 被占用 / run_id 与记录不一致。

    与普通 ValueError（参数错误 → 400）区分，供 API 层精确映射 HTTP 状态码。
    """


# 来源系统 → 注册爬虫映射（研招网/高校官网统一走 real_data；
# 该爬虫 store() 已改为写 PENDING 审核队列，不再直接落业务表）
_SOURCE_CRAWLER_MAP = {
    "yanzhao": "real_data",
    "school_official": "real_data",
}

# 人工触发时的护栏上限（合规红线：不批量抓取，研招网来源必须显式限量）
_TRIGGER_GUARD = {"max_pages": 1, "max_items": 50, "rate_limit": 1.0}


def _now() -> datetime:
    """与 audit 列一致的 naive UTC 时间。"""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _pending_count(db: Session, run_id: str) -> int:
    """统计某次运行仍处于 PENDING 的审核条目数。"""
    return (
        db.query(ExternalResearchItem.id)
        .filter(ExternalResearchItem.crawler_run_id == run_id)
        .filter(ExternalResearchItem.review_status == "PENDING")
        .count()
    )


# ----------------------------------------------------------------------
# 来源标注（t_data_source）
# ----------------------------------------------------------------------
def list_sources(
    db: Session,
    *,
    review_status: str | None,
    credibility: str | None,
    source_system: str | None,
    page: int,
    page_size: int,
) -> tuple[list[DataSourceMeta], int]:
    """来源与可信度配置分页列表（按 id 倒序，最新在前）。"""
    query = db.query(DataSourceMeta)
    if review_status:
        query = query.filter(DataSourceMeta.review_status == review_status)
    if credibility:
        query = query.filter(DataSourceMeta.credibility == credibility)
    if source_system:
        query = query.filter(DataSourceMeta.source_system == source_system)
    total = query.count()
    rows = (
        query.order_by(DataSourceMeta.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return rows, total


def update_source(
    db: Session,
    source_id: int,
    *,
    credibility: str | None,
    review_status: str | None,
    verify_count: int | None,
    reviewer: str,
) -> DataSourceMeta:
    """更新来源可信度配置（部分更新）；不存在抛 LookupError（由 API 层转 404）。"""
    source = db.query(DataSourceMeta).filter(DataSourceMeta.id == source_id).first()
    if source is None:
        raise LookupError("来源不存在")
    if credibility is not None:
        source.credibility = credibility
    if verify_count is not None:
        source.verify_count = verify_count
    if review_status is not None:
        source.review_status = review_status
        source.reviewed_by = reviewer
    db.commit()
    db.refresh(source)
    return source


def _ensure_source_meta(db: Session, ext_item: ExternalResearchItem, source_system: str) -> None:
    """来源标注（合规红线）：确认时确保 t_data_source 存在，无则建 PENDING 待核。

    随后的 promote_external_item._backfill_data_source 会将该行翻为 APPROVED
    并回填审核人（前提是本函数先于 promote 调用）。
    """
    existing = (
        db.query(DataSourceMeta).filter(DataSourceMeta.source_url == ext_item.source_url).first()
    )
    if existing is not None:
        return
    db.add(
        DataSourceMeta(
            source_system=source_system or "web",
            source_url=ext_item.source_url,
            crawled_at=_now(),
            credibility=ext_item.credibility,
            review_status="PENDING",
        )
    )
    # 显式 flush：后续 promote 的 _backfill_data_source 按 source_url 查询需先看到本行
    # （测试会话 autoflush=False 时，pending add 不触发自动 flush）
    db.flush()


# ----------------------------------------------------------------------
# 人工触发（POST /ingest）
# ----------------------------------------------------------------------
def trigger_ingest(
    db: Session,
    *,
    source_system: str,
    url: str | None,
    target_type: str | None,
) -> dict:
    """人工触发已注册爬虫，同步执行并把产物写入 PENDING 审核队列。

    - 仅支持能映射到已注册爬虫的来源系统（yanzhao / school_official）；
      manual 来源请直接用 POST /confirm 确认（无爬虫可触发）。
    - 护栏强制生效（max_pages=1 / max_items=50 / rate_limit=1s），
      即使配置文件未声明，人工触发也不放宽（合规红线：不批量抓取研招网）。
    - 爬虫 store() 自行创建 CrawlerRun 并写审核队列；本函数回读最新一次运行。

    Returns: 与 IngestRunVO 对齐的 dict。
    """
    crawler_name = _SOURCE_CRAWLER_MAP.get(source_system)
    if crawler_name is None:
        raise ValueError(
            f"来源系统 '{source_system}' 不支持自动触发（manual 请直接用 /confirm 确认来源）"
        )
    cls = get_crawler(crawler_name)
    if cls is None:
        raise LookupError(f"爬虫 '{crawler_name}' 未注册")

    config = load_config(crawler_name) or {}
    config.update(_TRIGGER_GUARD)
    crawler = cls(config=config)
    logger.info(
        "人工触发爬虫 source_system=%s crawler=%s url=%s target_type=%s",
        source_system,
        crawler_name,
        url,
        target_type,
    )
    result = crawler.run(db=db)  # 同步执行；store() 写 PENDING 队列并建 CrawlerRun

    run_record = (
        db.query(CrawlerRun)
        .filter(CrawlerRun.source_name == crawler_name)
        .order_by(CrawlerRun.created_at.desc())
        .first()
    )
    if run_record is None:
        raise RuntimeError(f"爬虫运行后未产生运行记录: {result}")
    run_id = str(run_record.id)
    return {
        "run_id": run_id,
        "source_system": source_system,
        "status": result.get("status", "unknown"),
        "total_items": run_record.stored_count,
        "pending_items": _pending_count(db, run_id),
        "created_time": run_record.created_at,
    }


def get_ingest_run(db: Session, run_id: str) -> dict:
    """查询一次抓取运行状态（映射 CrawlerRun）；不存在抛 LookupError（API 层转 404）。"""
    try:
        run_uuid = UUID(str(run_id))
    except ValueError:
        raise LookupError("run_id 必须是有效 UUID")
    run_record = db.query(CrawlerRun).filter(CrawlerRun.id == run_uuid).first()
    if run_record is None:
        raise LookupError("运行记录不存在")
    run_id_str = str(run_record.id)
    return {
        "run_id": run_id_str,
        "source_system": (
            "yanzhao"
            if run_record.source_name in _SOURCE_CRAWLER_MAP.values()
            else run_record.source_name
        ),
        "status": run_record.status,
        "total_items": run_record.stored_count,
        "pending_items": _pending_count(db, run_id_str),
        "created_time": run_record.created_at,
    }


# ----------------------------------------------------------------------
# 人工确认入库（POST /confirm）
# ----------------------------------------------------------------------
def confirm_ingest(
    db: Session,
    *,
    record_id: int,
    run_id: str,
    confirmed_fields: dict,
    source_url: str,
    source_system: str,
    operator_id: int,
    note: str | None,
    reviewer: str,
) -> dict:
    """人工确认字段入库（禁止自动入库，唯一落业务表通道）。

    流程：校验 PENDING → 来源 URL 追溯更新 → 写入 confirmed_fields →
    确保来源标注 → promote 落业务表（幂等）→ 队列/条目回填 APPROVED。
    同一事务内完成，异常统一回滚（由 API 层捕获转 HTTP）。

    Returns: 与 IngestRecordVO 对齐的 dict。
    """
    ext_item = db.query(ExternalResearchItem).filter(ExternalResearchItem.id == record_id).first()
    if ext_item is None:
        raise LookupError("待确认记录不存在")
    if ext_item.review_status != "PENDING":
        raise IngestionConflictError(
            f"该记录已审核（当前状态: {ext_item.review_status}），不可重复确认"
        )
    if run_id and str(ext_item.crawler_run_id) != str(run_id):
        raise IngestionConflictError("run_id 与记录所属运行不一致")

    # 来源 URL（合规红线 N1：公告原文链接必填，来源追溯）
    url = (source_url or "").strip()
    if url and url != ext_item.source_url:
        conflict = (
            db.query(ExternalResearchItem.id)
            .filter(ExternalResearchItem.source_url == url)
            .filter(ExternalResearchItem.id != ext_item.id)
            .first()
        )
        if conflict:
            raise IngestionConflictError("来源 URL 已被其他记录占用，无法更新")
        ext_item.source_url = url[:500]
    elif not ext_item.source_url:
        raise ValueError("source_url 必填（来源追溯，合规红线）")

    # 人工确认字段与审核信息写入 external_meta（行级来源元数据）
    meta = dict(ext_item.external_meta or {})
    meta["confirmed_fields"] = confirmed_fields
    if operator_id:
        meta["confirm_operator_id"] = operator_id
    if note:
        meta["confirm_note"] = note

    _ensure_source_meta(db, ext_item, source_system)
    promote_external_item(db, ext_item, reviewer)

    now = _now()
    ext_item.review_status = "APPROVED"
    ext_item.external_meta = meta
    queue_item = (
        db.query(ReviewQueueItem)
        .filter(
            ReviewQueueItem.ref_item_id == ext_item.id,
            ReviewQueueItem.item_type == "external_research",
        )
        .first()
    )
    if queue_item is not None:
        queue_item.review_status = "APPROVED"
        queue_item.reviewed_by = reviewer
        queue_item.reviewed_time = now
    db.commit()
    logger.info(
        "人工确认入库 record_id=%s reviewer=%s source_url=%s",
        ext_item.id,
        reviewer,
        ext_item.source_url,
    )
    return {
        "record_id": ext_item.id,
        "run_id": str(ext_item.crawler_run_id),
        "source_url": ext_item.source_url,
        "confirmed_fields": confirmed_fields,
        "status": "approved",
        "created_time": ext_item.created_time,
    }
