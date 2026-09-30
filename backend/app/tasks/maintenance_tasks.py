"""维护类定时任务——分数线年度心跳（DF-12，2026-09-29）+ 研招简章年度心跳（DF-21，2026-09-30）。

设计约束：
- 独立 job 前缀 `maintenance_`：B0 增删平衡（seed_default_schedules）只清理
  `crawler_` 前缀的残留 job，维护 job 不在白名单/线注册表体系内，走独立种子。
- 分数线是年更静态数据（每年 3 月中发布季更新），不进小时级爬虫管道；
  心跳位让 data_freshness 看板在数据变陈时可见（T6"静态快照"教训的对症）。
- annual_scoreline_refresh 复用 scripts/import_scoreline_official.py 的幂等管道
  （(校,专业,学位,年) 先查后插，重跑安全已实证）。

种子：seed_maintenance_jobs() 在应用启动时调用（幂等，Redis jobstore 重启不丢）。
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import text

from app.database import SessionLocal

logger = logging.getLogger(__name__)

SCORELINE_SOURCE_NAME = "scoreline_official"
ANNUAL_JOB_ID = "maintenance_scoreline_annual"
# 复试线发布季：每年 3 月中（国家线 3 月上旬、自划线 3 月中旬陆续公示）
ANNUAL_CRON = dict(month=3, day=15, hour=6, minute=0)

# DF-21：简章是强季节性数据（9-10 月发布高峰，部分校 10 月底才发），
# 错过窗口再等一年——与 DF-12 修前的分数线同一个病，同配方修。
YANZHAO_SOURCE_NAME = "yanzhao_official"
YANZHAO_ANNUAL_JOB_ID = "maintenance_yanzhao_annual"
# 简章季开跑前重跑幂等导入管道：每年 9-15 06:00 北京时
YANZHAO_ANNUAL_CRON = dict(month=9, day=15, hour=6, minute=0)


def upsert_scoreline_heartbeat() -> None:
    """回写 data_freshness 心跳行（last_success=now，records=当前行数）。

    表不存在（个别开发环境未迁移）时静默跳过；心跳缺失只影响看板可见性，
    不影响任何业务读取。
    """
    from app.models.grad_intel import GradScorelineRecord

    with SessionLocal() as db:
        try:
            records = db.query(GradScorelineRecord).count()
            db.execute(
                text(
                    "INSERT INTO data_freshness "
                    "(source_name, last_successful_crawl, records_count, status, updated_at) "
                    "VALUES (:n, NOW(), :c, 'active', NOW()) "
                    "ON CONFLICT (source_name) DO UPDATE SET "
                    "last_successful_crawl=NOW(), records_count=:c, status='active', updated_at=NOW()"
                ),
                {"n": SCORELINE_SOURCE_NAME, "c": records},
            )
            db.commit()
            logger.info("scoreline 心跳已回写: records=%s", records)
        except Exception as e:  # noqa: BLE001
            db.rollback()
            logger.warning("scoreline 心跳回写跳过（表可能不存在）: %s", e)


def annual_scoreline_refresh() -> dict:
    """年度任务：重跑官方分数线幂等导入管道 + 回写心跳。

    数据批次 JSON 随镜像分发（backend/scripts/data/scoreline_batch_*.json）；
    新一年批次由开发侧入库仓库后随部署生效，本任务只做重跑与心跳。
    """
    result: dict = {"ran_at": datetime.now(timezone.utc).isoformat()}
    try:
        from scripts.import_scoreline_official import main as import_main

        import_main()
        result["import"] = "ok"
    except Exception as e:  # noqa: BLE001
        result["import"] = f"error: {e}"
        logger.exception("年度分数线导入失败")
    try:
        upsert_scoreline_heartbeat()
        result["heartbeat"] = "ok"
    except Exception as e:  # noqa: BLE001
        result["heartbeat"] = f"error: {e}"
    return result


def upsert_yanzhao_heartbeat() -> None:
    """回写简章 data_freshness 心跳行（last_success=now，records=当前行数）。

    表不存在（个别开发环境未迁移）时静默跳过；心跳缺失只影响看板可见性，
    不影响任何业务读取。
    """
    from app.models.grad_intel import GradYanzhaoProgram

    with SessionLocal() as db:
        try:
            records = db.query(GradYanzhaoProgram).count()
            db.execute(
                text(
                    "INSERT INTO data_freshness "
                    "(source_name, last_successful_crawl, records_count, status, updated_at) "
                    "VALUES (:n, NOW(), :c, 'active', NOW()) "
                    "ON CONFLICT (source_name) DO UPDATE SET "
                    "last_successful_crawl=NOW(), records_count=:c, status='active', updated_at=NOW()"
                ),
                {"n": YANZHAO_SOURCE_NAME, "c": records},
            )
            db.commit()
            logger.info("yanzhao 心跳已回写: records=%s", records)
        except Exception as e:  # noqa: BLE001
            db.rollback()
            logger.warning("yanzhao 心跳回写跳过（表可能不存在）: %s", e)


def annual_yanzhao_refresh() -> dict:
    """年度任务：重跑研招简章幂等导入管道 + 回写心跳。

    复用 scripts/import_yanzhao_2027.py（(校,专业,年) 先查后插，唯一索引
    ix_yanzhao_unique=(university,major,year) 不含 degree_type 已对齐）；
    2028 起新年份批次扩写该导入脚本（或新增批次文件），本任务只做重跑与心跳。
    """
    result: dict = {"ran_at": datetime.now(timezone.utc).isoformat()}
    try:
        from scripts.import_yanzhao_2027 import main as import_main

        import_main()
        result["import"] = "ok"
    except Exception as e:  # noqa: BLE001
        result["import"] = f"error: {e}"
        logger.exception("年度简章导入失败")
    try:
        upsert_yanzhao_heartbeat()
        result["heartbeat"] = "ok"
    except Exception as e:  # noqa: BLE001
        result["heartbeat"] = f"error: {e}"
    return result


def seed_maintenance_jobs() -> None:
    """启动时注册维护类 job（幂等；与 crawler_ 种子互不干扰）。"""
    try:
        from app.api.crawlers import get_scheduler

        scheduler = get_scheduler()
        if not scheduler:
            logger.warning("APScheduler 未可用，跳过维护类定时任务注册")
            return
        for job_id, fn, cron, desc in (
            (ANNUAL_JOB_ID, annual_scoreline_refresh, ANNUAL_CRON, "每年 3-15 06:00"),
            (
                YANZHAO_ANNUAL_JOB_ID,
                annual_yanzhao_refresh,
                YANZHAO_ANNUAL_CRON,
                "每年 9-15 06:00",
            ),
        ):
            if scheduler.get_job(job_id) is None:
                scheduler.add_job(
                    fn,
                    "cron",
                    id=job_id,
                    replace_existing=True,
                    timezone="Asia/Shanghai",
                    **cron,
                )
                logger.info("已注册维护任务 %s（%s）", job_id, desc)
    except Exception as e:  # noqa: BLE001
        logger.warning("维护任务注册失败（不影响启动）: %s", e)
    # 心跳行补齐：无论 job 是否新注册，启动即回写一次（当前行数在场）
    for hb in (upsert_scoreline_heartbeat, upsert_yanzhao_heartbeat):
        try:
            hb()
        except Exception as e:  # noqa: BLE001
            logger.warning("%s 启动回写失败: %s", hb.__name__, e)
