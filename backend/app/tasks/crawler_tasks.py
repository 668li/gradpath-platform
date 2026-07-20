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

import asyncio
import logging
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

        run_record = CrawlerRun(
            source_name=source_name,
            category=crawler.category,
            status="running",
        )
        db.add(run_record)
        db.commit()
        db.refresh(run_record)

        result = crawler.run(db=db) if not dry_run else {"status": "dry_run"}

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

        run_record = CrawlerRun(
            source_name=source_name,
            category=crawler.category,
            status="running",
        )
        db.add(run_record)
        db.commit()
        db.refresh(run_record)

        result = crawler.run(db=db)

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
                ws_manager.broadcast_sync({
                    "type": "data_update",
                    "source_name": source_name,
                    "items_stored": result.get("stored", 0),
                })
            except Exception as e:
                logger.warning("定时任务数据更新通知失败: %s", e)

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
