"""爬虫 Celery 任务 — 替代 FastAPI BackgroundTasks。

任务路由：app.tasks.crawler_tasks.* → crawler 队列
执行入口：
- run_crawler_task：用户触发的爬虫执行（原 _run_crawler_background）
- run_scheduled_crawler_task：APScheduler 定时触发的爬虫执行（原 _run_scheduled_crawler）

兼容入口：
- _run_crawler_background：保留原签名，内部调用 celery task.delay()
  当 Celery broker 不可用时，自动降级到同步执行（不阻塞 FastAPI worker）。
"""

from __future__ import annotations

import logging
import math
import time
from datetime import datetime, timezone
from uuid import uuid4

from app.celery_app import celery_app
from app.core.cache import cache
from app.core.websocket_manager import manager as ws_manager
from app.crawlers.crawler_config import load_config
from app.crawlers.registry import get_crawler
from app.database import SessionLocal
from app.models.crawler_run import CrawlerRun

logger = logging.getLogger(__name__)

TASK_CACHE_PREFIX = "crawler_task"
TASK_CACHE_TTL = 24 * 60 * 60


def _resolve_run_record(
    db, source_name: str, category: str, result: dict, crawler
) -> CrawlerRun:
    """单行记账：取爬虫 store() 建的行（result.run_id）；未建行时兜底补一行。

    行以爬虫内部创建为准（run_id 溯源链在爬虫手上），包装层只更新不另建；
    dry_run / store 建行前失败等场景爬虫未建行，这里补一行保持执行记录不丢，
    并回填 started_at / duration_seconds（dry_run 无计时则留空）。
    """
    run_id = result.get("run_id")
    if run_id:
        record = db.get(CrawlerRun, run_id)
        if record is not None:
            return record
    started_at = getattr(crawler, "_run_started_at", "") or None
    started_mono = getattr(crawler, "_run_start_monotonic", 0.0)
    record = CrawlerRun(
        source_name=source_name,
        category=category,
        status="running",
        started_at=started_at,
    )
    if started_mono > 0:
        elapsed = time.monotonic() - started_mono
        record.duration_seconds = max(1, math.ceil(elapsed))
        record.finished_at = datetime.now(timezone.utc).isoformat()
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@celery_app.task(name="app.tasks.crawler_tasks.run_crawler_task", bind=True)
def run_crawler_task(self, task_id: str, source_name: str, dry_run: bool = False):
    """Celery 任务：执行爬虫并发送 WebSocket 进度通知。

    Args:
        task_id: 任务追踪 ID（由 API 层生成）
        source_name: 爬虫源名称
        dry_run: 是否只模拟执行（不写库）
    """
    db = SessionLocal()
    try:
        cache.set(
            f"{TASK_CACHE_PREFIX}:{task_id}",
            {"status": "running", "source_name": source_name},
            ttl=TASK_CACHE_TTL,
        )
        ws_manager.notify_task_sync(task_id, "running", {"source_name": source_name})

        cls = get_crawler(source_name)
        if not cls:
            cache.set(
                f"{TASK_CACHE_PREFIX}:{task_id}",
                {"status": "failed", "error": f"爬虫 '{source_name}' 未注册"},
                ttl=TASK_CACHE_TTL,
            )
            ws_manager.notify_task_sync(
                task_id, "failed", {"error": f"爬虫 '{source_name}' 未注册"}
            )
            return {"status": "failed", "error": f"爬虫 '{source_name}' 未注册"}

        config = load_config(source_name)
        crawler = cls(config=config)

        result = crawler.run(db=db) if not dry_run else {"status": "dry_run"}

        # 单行记账：行由爬虫 store() 创建（溯源链在爬虫手上），包装层只更新；
        # 爬虫未建行（dry_run / 建行前失败）时兜底补一行，执行记录不丢。
        run_record = _resolve_run_record(db, source_name, crawler.category, result, crawler)

        run_record.status = result.get("status", "unknown")
        run_record.items_fetched = result.get("fetched", 0)
        run_record.items_stored = result.get("stored", 0)
        run_record.items_duplicates = result.get("duplicates", 0)
        run_record.error_count = result.get("errors", 0)
        run_record.error_message = result.get("error")
        db.commit()
        db.refresh(run_record)

        cache.set(
            f"{TASK_CACHE_PREFIX}:{task_id}",
            {
                "status": result.get("status", "unknown"),
                "run_id": str(run_record.id),
                "fetched": result.get("fetched", 0),
                "stored": result.get("stored", 0),
                "errors": result.get("errors", 0),
            },
            ttl=TASK_CACHE_TTL,
        )
        ws_manager.notify_task_sync(
            task_id,
            result.get("status", "unknown"),
            {
                "run_id": str(run_record.id),
                "fetched": result.get("fetched", 0),
                "stored": result.get("stored", 0),
                "errors": result.get("errors", 0),
            },
        )
        logger.info("爬虫 %s 执行完成: %s", source_name, result)
        return result

    except Exception as e:
        logger.error("爬虫 %s 执行失败: %s", source_name, e)
        cache.set(
            f"{TASK_CACHE_PREFIX}:{task_id}",
            {"status": "failed", "error": str(e)},
            ttl=TASK_CACHE_TTL,
        )
        ws_manager.notify_task_sync(task_id, "failed", {"error": str(e)})
        return {"status": "failed", "error": str(e)}
    finally:
        db.close()


@celery_app.task(name="app.tasks.crawler_tasks.run_scheduled_crawler_task")
def run_scheduled_crawler_task(source_name: str):
    """Celery 任务：APScheduler 定时触发的爬虫执行。

    与 run_crawler_task 区别：不向 task_id 通道推送进度（定时任务无前端订阅），
    但仍写入 CrawlerRun 记录并广播 data_update 通知。

    Args:
        source_name: 爬虫源名称
    """
    task_id = uuid4().hex[:12]
    logger.info("定时爬虫任务触发: %s, task_id=%s", source_name, task_id)

    db = SessionLocal()
    try:
        cls = get_crawler(source_name)
        if not cls:
            logger.error("定时爬虫 '%s' 未注册", source_name)
            return {"status": "failed", "error": f"爬虫 '{source_name}' 未注册"}

        config = load_config(source_name)
        crawler = cls(config=config)

        result = crawler.run(db=db)

        # 单行记账：行由爬虫 store() 创建（溯源链在爬虫手上），包装层只更新；
        # 爬虫未建行（建行前失败）时兜底补一行，执行记录不丢。
        run_record = _resolve_run_record(db, source_name, crawler.category, result, crawler)

        run_record.status = result.get("status", "unknown")
        run_record.items_fetched = result.get("fetched", 0)
        run_record.items_stored = result.get("stored", 0)
        run_record.items_duplicates = result.get("duplicates", 0)
        run_record.error_count = result.get("errors", 0)
        run_record.error_message = result.get("error")
        db.commit()

        # 通过 WebSocket 广播数据更新通知（跨 worker）
        if result.get("stored", 0) > 0:
            try:
                # broadcast_sync 调度协程到主事件循环；
                # Celery worker 无主事件循环时，使用 asyncio.run 降级
                ws_manager.broadcast_sync(
                    {
                        "type": "data_update",
                        "source_name": source_name,
                        "items_stored": result.get("stored", 0),
                    }
                )
            except Exception as e:
                logger.warning("定时任务数据更新通知失败: %s", e)

            # 三闸门自动放行（来源信誉+质量分+红线）：新数据不再滞留审核队列。
            # 独立会话 + 全量异常兜底，绝不影响采集主流程。
            try:
                from app.database import SessionLocal as _SL
                from app.services.research_auto_review import auto_review_pending

                with _SL() as review_db:
                    review_stats = auto_review_pending(review_db)
                if review_stats.get("auto_approved") or review_stats.get("chsi_rejected"):
                    logger.info("定时爬虫 %s 自动放行: %s", source_name, review_stats)
            except Exception as e:
                logger.warning("自动放行失败（不影响采集）: %s", e)

        logger.info("定时爬虫 %s 完成: %s", source_name, result)
        return result

    except Exception as e:
        logger.error("定时爬虫 %s 失败: %s", source_name, e)
        return {"status": "failed", "error": str(e)}
    finally:
        db.close()


# ----------------------------------------------------------------------
# 兼容入口：供 API 层与 APScheduler 调用
# 优先使用 Celery 异步执行；broker 不可用时降级到同步执行
# ----------------------------------------------------------------------


def _celery_available() -> bool:
    """检查 Celery broker 是否可用（仅检查配置，不发实际连接）。"""
    from app.config import settings

    if not settings.REDIS_URL:
        return False
    try:
        # celery_app.connection().ensure_connection 会发起实际连接，
        # 这里仅检查 broker URL 是否非 memory://，避免引入网络 IO
        return not str(celery_app.conf.broker_url).startswith("memory://")
    except Exception:
        return False


def _run_crawler_background_compat(
    task_id: str,
    source_name: str,
    dry_run: bool = False,
):
    """兼容入口：原 _run_crawler_background 签名。

    优先调用 Celery task.delay() 异步执行；
    Celery 不可用时降级到同步直接执行（仅开发环境，会阻塞 FastAPI worker）。
    """
    if _celery_available():
        try:
            run_crawler_task.delay(task_id, source_name, dry_run)
            return
        except Exception as e:
            logger.warning("Celery 任务投递失败，降级同步执行: %s", e)
    # 降级：同步执行
    run_crawler_task.run(task_id, source_name, dry_run)


def _run_scheduled_crawler_compat(source_name: str):
    """兼容入口：APScheduler 定时任务调用。

    优先使用 Celery 任务；不可用时同步执行。
    """
    if _celery_available():
        try:
            run_scheduled_crawler_task.delay(source_name)
            return
        except Exception as e:
            logger.warning("Celery 任务投递失败，降级同步执行: %s", e)
    run_scheduled_crawler_task.run(source_name)
