"""Celery 应用实例 — GradPath 分布式任务队列。

- broker/backend: Redis（与 FastAPI / slowapi / APScheduler 共用）
- 任务路由：crawler_tasks → crawler 队列；ai_tasks → ai 队列；默认 default 队列
- 可靠性：task_acks_late + task_reject_on_worker_lost 保证 worker 崩溃后任务重投
- 资源控制：worker_max_tasks_per_child=100 防止内存泄漏；prefetch=1 防止长任务饥饿
- 超时：硬超时 30 分钟，软超时 25 分钟（爬虫/AI 任务可能耗时较长）
"""
from __future__ import annotations

import logging

from celery import Celery

from app.config import settings

logger = logging.getLogger(__name__)


def _build_celery_broker_url() -> str:
    """构建 Celery broker URL，未配置 Redis 时返回内存 broker（仅开发/测试用）。

    生产环境 settings.REDIS_URL 必须配置（见 config.py 强制校验）。
    """
    if settings.REDIS_URL:
        return settings.REDIS_URL
    return "memory://"


celery_app = Celery(
    "gradpath",
    broker=_build_celery_broker_url(),
    backend=_build_celery_broker_url(),
    include=["app.tasks.crawler_tasks", "app.tasks.ai_tasks"],
)

celery_app.conf.update(
    # 序列化
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    # 时区
    timezone="Asia/Shanghai",
    enable_utc=True,
    # 任务可见性
    task_track_started=True,
    # 超时：硬超时 30 分钟，软超时 25 分钟
    task_time_limit=30 * 60,
    task_soft_time_limit=25 * 60,
    # Worker 行为
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=100,
    # 可靠性：worker 崩溃后任务重投
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    # 队列路由
    task_default_queue="default",
    task_routes={
        "app.tasks.crawler_tasks.*": {"queue": "crawler"},
        "app.tasks.ai_tasks.*": {"queue": "ai"},
    },
)

logger.info("Celery 应用已初始化: broker=%s", _build_celery_broker_url())
