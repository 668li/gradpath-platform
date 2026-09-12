"""爬虫线状态服务（数据地基④⑥，spec 002 FR3/FR5）。

每条爬虫线在 t_crawler_source_state 恰一行的持久化状态：
- 增量游标（cursor/etag/last_modified）：运行前读、成功后写，断点续爬与增量判定的依据；
- last_ok_at / consecutive_fails / isolated：死线必被知的判定与自动隔离。

心跳（data_freshness）由本服务统一回写——10 源全覆盖，替代各爬虫手写段
（原仅 eol_kaoyan 回写）。失败也记账（status="failed"），新鲜度看板即时可见。
"""

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.crawler_run import CrawlerRun  # noqa: F401  — 保持模型注册次序稳定
from app.models.crawler_state import CrawlerSourceState
from app.models.ingestion import DataFreshness

logger = logging.getLogger(__name__)

# 连续失败达到该值即自动隔离（地基⑥：死线不污染活库，调度器跳过）
ISOLATE_AFTER_CONSECUTIVE_FAILS = 2


def _now() -> datetime:
    return datetime.now(timezone.utc)


def get_or_create_state(db: Session, source_name: str) -> CrawlerSourceState:
    state = db.query(CrawlerSourceState).filter(CrawlerSourceState.source_name == source_name).first()
    if state is None:
        state = CrawlerSourceState(source_name=source_name)
        db.add(state)
        db.flush()
    return state


def is_isolated(db: Session, source_name: str) -> bool:
    """该线是否处于隔离态（调度器据此跳过）。状态行不存在 = 未隔离。"""
    row = (
        db.query(CrawlerSourceState)
        .filter(CrawlerSourceState.source_name == source_name, CrawlerSourceState.isolated.is_(True))
        .first()
    )
    return row is not None


def load_cursor(db: Session, source_name: str) -> dict | None:
    """读取该线的增量游标（无行/无游标返回 None = 全量语义）。"""
    state = (
        db.query(CrawlerSourceState).filter(CrawlerSourceState.source_name == source_name).first()
    )
    return state.cursor if state else None


def record_run_result(
    db: Session,
    source_name: str,
    *,
    ok: bool,
    cursor: dict | None = None,
    error: str | None = None,
) -> None:
    """一次运行终态回写：成功清零失败计数并写游标；失败累加，达阈值自动隔离。

    隔离只置位不删数据；解除是显式人工动作（unisolate）。
    本函数自带 flush，不 commit——调用方事务语义由爬虫 run() 统一管理。
    """
    state = get_or_create_state(db, source_name)
    state.last_run_at = _now()
    state.updated_at = _now()
    if ok:
        state.last_ok_at = _now()
        state.consecutive_fails = 0
        if cursor is not None:
            state.cursor = cursor
        return
    state.consecutive_fails = (state.consecutive_fails or 0) + 1
    if state.consecutive_fails >= ISOLATE_AFTER_CONSECUTIVE_FAILS and not state.isolated:
        state.isolated = True
        state.isolated_reason = (
            f"连续 {state.consecutive_fails} 次运行失败自动隔离"
            f"{'：' + str(error)[:200] if error else ''}"
        )
        logger.error("[crawler_state] %s 已自动隔离: %s", source_name, state.isolated_reason)


def record_heartbeat(db: Session, source_name: str, *, ok: bool, inserted: int = 0) -> None:
    """data_freshness 心跳统一回写（10 源全覆盖）。

    ok：last_successful_crawl=now、records_count 累加、status=active；
    失败：status=failed（last_successful_crawl 不动——新鲜度老化的诚实口径）。
    """
    fresh = db.query(DataFreshness).filter(DataFreshness.source_name == source_name).first()
    now = _now()
    if fresh is None:
        fresh = DataFreshness(source_name=source_name)
        db.add(fresh)
    if ok:
        fresh.last_successful_crawl = now
        fresh.records_count = (fresh.records_count or 0) + max(0, inserted)
    fresh.status = "active" if ok else "failed"
    fresh.updated_at = now


def unisolate(db: Session, source_name: str, *, by: str = "admin") -> bool:
    """显式解除隔离（人工动作）：清零失败计数、清理由人。返回是否存在隔离行。"""
    state = db.query(CrawlerSourceState).filter(CrawlerSourceState.source_name == source_name).first()
    if state is None or not state.isolated:
        return False
    logger.warning("[crawler_state] %s 解除隔离（by=%s，原由：%s）", source_name, by, state.isolated_reason)
    state.isolated = False
    state.isolated_reason = None
    state.consecutive_fails = 0
    state.updated_at = _now()
    db.commit()
    return True
