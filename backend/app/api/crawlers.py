"""爬虫管理 API — 管理员专用。支持异步执行、APScheduler定时任务和WebSocket通知。"""
import json
import logging
from uuid import uuid4
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

# 后台爬虫任务为 sync 函数（在线程池执行），通过 ws_manager.notify_task_sync
# 把跨 worker 的 WebSocket 广播协程调度到主事件循环。

from app.core.deps import get_admin_user
from app.core.cache import cache
from app.config import settings
from app.database import get_db, SessionLocal
from app.models.user import User
from app.models.crawler_run import CrawlerRun
from app.schemas.crawler_run import CrawlerInfo, CrawlerRunRequest, CrawlerRunResponse
from app.crawlers.registry import list_crawlers, get_crawler
from app.crawlers.crawler_config import load_config
from app.core.websocket_manager import manager as ws_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/crawlers", tags=["爬虫管理"])

# 优化：爬虫任务状态使用 Redis 缓存（自动降级内存），多 worker 共享
# 原 _task_status dict 进程重启丢失 + 多 worker 不共享
TASK_CACHE_PREFIX = "crawler_task"
TASK_CACHE_TTL = 24 * 60 * 60  # 24 hours


def _celery_available() -> bool:
    """检查 Celery 是否可用（仅检查配置，不发实际连接）。"""
    if not settings.REDIS_URL:
        return False
    try:
        from app.celery_app import celery_app
        broker_url = str(celery_app.conf.broker_url or "")
        return not broker_url.startswith("memory://")
    except Exception:
        return False


def _dispatch_crawler_task(task_id: str, source_name: str, dry_run: bool):
    """投递爬虫任务到 Celery；不可用时降级到 FastAPI BackgroundTasks。

    由调用方决定降级路径（API 端点用 BackgroundTasks 兜底）。
    """
    if _celery_available():
        try:
            from app.tasks.crawler_tasks import run_crawler_task
            run_crawler_task.delay(task_id, source_name, dry_run)
            logger.info("爬虫任务已投递到 Celery: task_id=%s source=%s", task_id, source_name)
            return True
        except Exception as e:
            logger.warning("Celery 投递失败，降级到 BackgroundTasks: %s", e)
    return False

# ----------------------------------------------------------------------
# APScheduler 定时任务管理
# ----------------------------------------------------------------------
_scheduler = None


def _build_scheduler_jobstore():
    """构建 APScheduler jobstore：优先使用 Redis 后端（多 worker 共享），
    
    Redis 不可用时降级到 MemoryJobStore（开发环境）。
    修复: A9 — 原 MemoryJobStore 进程重启后任务丢失，多 worker 重复执行定时任务。
    """
    from apscheduler.jobstores.memory import MemoryJobStore

    if not settings.REDIS_URL:
        logger.info("APScheduler 使用 MemoryJobStore（未配置 REDIS_URL，开发环境）")
        return MemoryJobStore()

    try:
        from urllib.parse import urlparse
        from apscheduler.jobstores.redis import RedisJobStore

        # 解析 redis://[:password@]host:port/db
        parsed = urlparse(settings.REDIS_URL)
        host = parsed.hostname or "localhost"
        port = parsed.port or 6379
        password = parsed.password
        db = int(parsed.path.lstrip("/") or "0")

        jobstore = RedisJobStore(
            host=host,
            port=port,
            password=password,
            db=db,
        )
        logger.info(
            "APScheduler 使用 RedisJobStore: host=%s port=%d db=%d",
            host, port, db,
        )
        return jobstore
    except Exception as e:
        logger.warning(
            "Redis 不可用，APScheduler 降级到 MemoryJobStore"
            "（多 worker 可能重复执行定时任务）: %s",
            e,
        )
        return MemoryJobStore()


def get_scheduler():
    """延迟初始化APScheduler实例。"""
    global _scheduler
    if _scheduler is None:
        try:
            from apscheduler.schedulers.asyncio import AsyncIOScheduler
            _scheduler = AsyncIOScheduler(jobstores={"default": _build_scheduler_jobstore()})
            _scheduler.start()
            logger.info("APScheduler 已启动")
        except ImportError:
            logger.warning("apscheduler 未安装，定时任务功能不可用")
            return None
    return _scheduler


class ScheduleRequest(BaseModel):
    # 修复: FASTAPI-VALID-001 — 字符串字段加 max_length 防止超长输入导致日志膨胀 / DB 拒绝 / DoS
    source_name: str = Field(..., min_length=1, max_length=100, description="爬虫源名称")
    cron: str = Field(default="0 2 * * *", min_length=1, max_length=100, description="Cron 表达式")
    enabled: bool = True


class ScheduleResponse(BaseModel):
    job_id: str
    source_name: str
    cron: str
    enabled: bool
    next_run: str | None = None


@router.get("", response_model=list[CrawlerInfo])
def list_all_crawlers(user: User = Depends(get_admin_user)):
    """列出所有已注册爬虫。"""
    crawlers = list_crawlers()
    result = []
    for name, cls in crawlers.items():
        result.append(CrawlerInfo(
            name=name,
            category=cls.category,
            description=cls.description,
            config=load_config(name),
        ))
    return result


def _run_crawler_background(
    task_id: str,
    source_name: str,
    dry_run: bool = False,
):
    """后台执行爬虫任务。"""
    db = SessionLocal()
    try:
        # 更新状态为运行中
        cache.set(f"{TASK_CACHE_PREFIX}:{task_id}", {"status": "running", "source_name": source_name}, ttl=TASK_CACHE_TTL)
        
        # 发送WebSocket通知
        ws_manager.notify_task_sync(task_id, "running", {"source_name": source_name})

        cls = get_crawler(source_name)
        if not cls:
            cache.set(f"{TASK_CACHE_PREFIX}:{task_id}", {"status": "failed", "error": f"爬虫 '{source_name}' 未注册"}, ttl=TASK_CACHE_TTL)
            ws_manager.notify_task_sync(task_id, "failed", {"error": f"爬虫 '{source_name}' 未注册"})
            return
        
        config = load_config(source_name)
        crawler = cls(config=config)
        
        # 创建执行记录
        run_record = CrawlerRun(
            source_name=source_name,
            category=crawler.category,
            status="running",
        )
        db.add(run_record)
        db.commit()
        db.refresh(run_record)
        
        # 执行爬虫
        result = crawler.run(db=db) if not dry_run else {"status": "dry_run"}
        
        # 更新记录
        run_record.status = result.get("status", "unknown")
        run_record.items_fetched = result.get("fetched", 0)
        run_record.items_stored = result.get("stored", 0)
        run_record.items_duplicates = result.get("duplicates", 0)
        run_record.error_count = result.get("errors", 0)
        run_record.error_message = result.get("error")
        db.commit()
        db.refresh(run_record)
        
        # 更新任务状态
        cache.set(f"{TASK_CACHE_PREFIX}:{task_id}", {
            "status": result.get("status", "unknown"),
            "run_id": str(run_record.id),
            "fetched": result.get("fetched", 0),
            "stored": result.get("stored", 0),
            "errors": result.get("errors", 0),
        }, ttl=TASK_CACHE_TTL)
        
        # 发送WebSocket通知
        ws_manager.notify_task_sync(task_id, result.get("status", "unknown"), {
            "run_id": str(run_record.id),
            "fetched": result.get("fetched", 0),
            "stored": result.get("stored", 0),
            "errors": result.get("errors", 0),
        })

        logger.info(f"爬虫 {source_name} 执行完成: {result}")

    except Exception as e:
        logger.error(f"爬虫 {source_name} 执行失败: {e}")
        cache.set(f"{TASK_CACHE_PREFIX}:{task_id}", {"status": "failed", "error": str(e)}, ttl=TASK_CACHE_TTL)
        ws_manager.notify_task_sync(task_id, "failed", {"error": str(e)})
    finally:
        db.close()


@router.post("/run")
def run_crawler_endpoint(
    body: CrawlerRunRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_admin_user),
):
    """触发指定爬虫（异步执行，立即返回task_id）。

    优先投递到 Celery 队列；Celery 不可用时降级到 FastAPI BackgroundTasks 兜底。
    """
    cls = get_crawler(body.source_name)
    if not cls:
        raise HTTPException(status_code=404, detail=f"爬虫 '{body.source_name}' 未注册")

    task_id = uuid4().hex[:12]

    # 优先投递到 Celery；失败时降级到 BackgroundTasks
    dispatched = _dispatch_crawler_task(task_id, body.source_name, body.dry_run)
    if not dispatched:
        # Celery 不可用兜底：原 BackgroundTasks 同步执行
        background_tasks.add_task(
            _run_crawler_background,
            task_id=task_id,
            source_name=body.source_name,
            dry_run=body.dry_run,
        )
        message = "爬虫任务已通过 BackgroundTasks 启动（Celery 不可用降级）"
    else:
        message = "爬虫任务已投递到 Celery 队列"

    return {
        "task_id": task_id,
        "status": "started",
        "source_name": body.source_name,
        "message": f"{message}，请通过 /status/{task_id} 查询进度",
    }


@router.get("/status/{task_id}")
# 修复: FASTAPI-AUTHZ-001 — 任务状态可能包含爬取量、错误信息等运营敏感数据，
# 必须强制管理员鉴权，避免未授权用户枚举 task_id 获取爬虫运行情况
def get_task_status(
    task_id: str,
    user: User = Depends(get_admin_user),
):
    """查询爬虫任务状态。"""
    task_data = cache.get(f"{TASK_CACHE_PREFIX}:{task_id}")
    if not task_data:
        raise HTTPException(status_code=404, detail="任务不存在或已过期")
    return {"task_id": task_id, **task_data}


@router.get("/runs", response_model=list[CrawlerRunResponse])
def list_runs(
    limit: int = 50,
    source_name: str | None = None,
    user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """获取爬取历史记录。"""
    query = db.query(CrawlerRun)
    if source_name:
        query = query.filter(CrawlerRun.source_name == source_name)
    items = query.order_by(CrawlerRun.created_at.desc()).limit(limit).all()
    return [CrawlerRunResponse.model_validate(i) for i in items]


@router.get("/runs/{run_id}", response_model=CrawlerRunResponse)
def get_run_detail(
    run_id: str,
    user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """获取单次爬取详情。"""
    from uuid import UUID
    record = db.query(CrawlerRun).filter(CrawlerRun.id == UUID(run_id)).first()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    return CrawlerRunResponse.model_validate(record)


# ----------------------------------------------------------------------
# APScheduler 定时任务端点
# ----------------------------------------------------------------------
@router.get("/schedules", response_model=list[ScheduleResponse])
def list_schedules(user: User = Depends(get_admin_user)):
    """列出所有定时爬虫任务。"""
    scheduler = get_scheduler()
    if not scheduler:
        return []
    jobs = []
    for job in scheduler.get_jobs():
        if job.id.startswith("crawler_"):
            jobs.append(ScheduleResponse(
                job_id=job.id,
                source_name=job.kwargs.get("source_name", ""),
                cron=str(job.trigger),
                enabled=job.next_run_time is not None,
                next_run=str(job.next_run_time) if job.next_run_time else None,
            ))
    return jobs


@router.post("/schedules", response_model=ScheduleResponse)
def create_schedule(
    body: ScheduleRequest,
    user: User = Depends(get_admin_user),
):
    """创建定时爬虫任务。"""
    scheduler = get_scheduler()
    if not scheduler:
        raise HTTPException(status_code=503, detail="APScheduler 未可用")

    cls = get_crawler(body.source_name)
    if not cls:
        raise HTTPException(status_code=404, detail=f"爬虫 '{body.source_name}' 未注册")

    job_id = f"crawler_{body.source_name}"
    cron_parts = body.cron.split()
    trigger_kwargs = {
        "minute": cron_parts[0] if len(cron_parts) > 0 else "*",
        "hour": cron_parts[1] if len(cron_parts) > 1 else "*",
        "day": cron_parts[2] if len(cron_parts) > 2 else "*",
        "month": cron_parts[3] if len(cron_parts) > 3 else "*",
        "day_of_week": cron_parts[4] if len(cron_parts) > 4 else "*",
    }

    scheduler.add_job(
        _run_scheduled_crawler,
        "cron",
        id=job_id,
        kwargs={"source_name": body.source_name},
        replace_existing=True,
        **trigger_kwargs,
    )

    job = scheduler.get_job(job_id)
    return ScheduleResponse(
        job_id=job_id,
        source_name=body.source_name,
        cron=body.cron,
        enabled=True,
        next_run=str(job.next_run_time) if job and job.next_run_time else None,
    )


@router.delete("/schedules/{job_id}")
def delete_schedule(
    job_id: str,
    user: User = Depends(get_admin_user),
):
    """删除定时爬虫任务。"""
    scheduler = get_scheduler()
    if not scheduler:
        raise HTTPException(status_code=503, detail="APScheduler 未可用")

    job = scheduler.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="定时任务不存在")

    scheduler.remove_job(job_id)
    return {"status": "deleted", "job_id": job_id}


@router.patch("/schedules/{job_id}/toggle")
def toggle_schedule(
    job_id: str,
    user: User = Depends(get_admin_user),
):
    """启用/禁用定时爬虫任务。"""
    scheduler = get_scheduler()
    if not scheduler:
        raise HTTPException(status_code=503, detail="APScheduler 未可用")

    job = scheduler.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="定时任务不存在")

    if job.next_run_time is not None:
        scheduler.pause_job(job_id)
        enabled = False
    else:
        scheduler.resume_job(job_id)
        enabled = True

    job = scheduler.get_job(job_id)
    return {
        "job_id": job_id,
        "enabled": enabled,
        "next_run": str(job.next_run_time) if job and job.next_run_time else None,
    }


async def _run_scheduled_crawler(source_name: str):
    """APScheduler回调：投递爬虫任务到 Celery；不可用时降级同步执行。

    修改: A10 — 原 APScheduler 直接同步执行爬虫，多 worker 会重复执行同一任务；
    改为投递到 Celery 队列，由 Celery worker 单一消费保证幂等。
    """
    task_id = uuid4().hex[:12]
    logger.info(f"定时任务触发: {source_name}, task_id={task_id}")

    # 优先投递到 Celery 队列
    if _celery_available():
        try:
            from app.tasks.crawler_tasks import run_scheduled_crawler_task
            run_scheduled_crawler_task.delay(source_name)
            logger.info("定时爬虫任务已投递到 Celery: source=%s", source_name)
            return
        except Exception as e:
            logger.warning("Celery 投递失败，降级同步执行: %s", e)

    # Celery 不可用兜底：原同步执行逻辑（保留以维持向后兼容）
    db = SessionLocal()
    try:
        cls = get_crawler(source_name)
        if not cls:
            logger.error(f"定时爬虫 '{source_name}' 未注册")
            return

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

        # 发送数据更新回调通知（供n8n webhook接收）
        if result.get("stored", 0) > 0:
            await _notify_data_update(source_name, result.get("stored", 0))

        logger.info(f"定时爬虫 {source_name} 完成: {result}")
    except Exception as e:
        logger.error(f"定时爬虫 {source_name} 失败: {e}")
    finally:
        db.close()


async def _notify_data_update(source_name: str, items_stored: int):
    """发送数据更新通知（WebSocket + 外部webhook）。"""
    import httpx
    from app.config import settings

    # WebSocket广播
    await ws_manager.broadcast({
        "type": "data_update",
        "source_name": source_name,
        "items_stored": items_stored,
    })

    # 外部webhook（n8n）
    webhook_url = getattr(settings, "DATA_UPDATE_WEBHOOK_URL", None)
    if webhook_url:
        try:
            async with httpx.AsyncClient() as client:
                await client.post(webhook_url, json={
                    "source_name": source_name,
                    "items_stored": items_stored,
                }, timeout=10)
        except Exception as e:
            logger.warning(f"Webhook通知失败: {e}")
