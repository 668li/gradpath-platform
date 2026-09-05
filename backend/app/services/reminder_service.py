"""中断次日提醒服务（P1）— 让中断用户第二天被轻轻拉回。

目标：
- 每天 21:00（北京时间，Asia/Shanghai——容器时区是 UTC，必须显式指定，否则
  cron 会按 UTC 21:00 触发=北京时间凌晨 5 点）给「昨天完成了微行动任务、
  今天还没开始」的用户发一条站内 reminder 通知（NotificationType.reminder）。
- 文案克制：禁止倒计时/仅剩/最后机会等紧迫话术；同一用户同一天最多 1 条。
- 默认关闭：MICRO_ACTION_REMINDER_D2 = False，需显式开启。
- 测试环境（ENVIRONMENT == "test"）不注册真实 scheduler job。
"""

from __future__ import annotations

import logging
from datetime import date, datetime, time, timedelta, timezone
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.config import settings
from app.models.micro_action import MicroActionPlan, MicroActionTask
from app.models.notification import Notification
from app.models.streak import StreakRecord

logger = logging.getLogger(__name__)

REMINDER_JOB_ID = "micro_action_reminder_d2"

# 业务时间基准=用户所在时区（北京时间）。容器 UTC≠宿主机 CST，不许用系统本地时区。
REMINDER_TZ = ZoneInfo("Asia/Shanghai")

# 同一用户同一天最多 1 条提醒，且只提醒「中断次日」场景
REMINDER_TITLE = "昨天的探索还留着尾巴"
REMINDER_CONTENT = (
    "你昨天完成了一个微行动任务。今天有空的话，"
    "可以回到面板看看下一步是什么——不着急，按你的节奏来。"
)


def _local_today() -> date:
    """北京时间的今天（21:00 job 与"昨天/今天"边界都按此基准）。"""
    return datetime.now(REMINDER_TZ).date()


def find_d2_reminder_users(db: Session, today: date | None = None) -> list[UUID]:
    """筛选「昨天完成任务、今天还没开始」的用户。

    条件（全部满足）：
    - 用户名下存在 status=active 的微行动计划；
    - 昨天有该计划的 status=completed 的任务（completed_at 落在昨天本地日）；
    - 今天该用户还没有任何 StreakRecord（今天尚未产生真实行动）；
    - 今天尚未给该用户发过 reminder（同一天最多 1 条）。
    """
    day = today or _local_today()
    yesterday = day - timedelta(days=1)
    day_start = datetime.combine(yesterday, time.min, tzinfo=REMINDER_TZ)
    day_end = datetime.combine(day, time.min, tzinfo=REMINDER_TZ)

    # 昨天完成过任务的用户（按 plan 归属）
    rows = (
        db.query(MicroActionPlan.user_id)
        .join(MicroActionTask, MicroActionTask.plan_id == MicroActionPlan.id)
        .filter(
            MicroActionPlan.status == "active",
            MicroActionTask.status == "completed",
            MicroActionTask.completed_at >= day_start,
            MicroActionTask.completed_at < day_end,
        )
        .distinct()
        .all()
    )
    candidate_ids = [row[0] for row in rows]
    if not candidate_ids:
        return []

    result: list[UUID] = []
    for user_id in candidate_ids:
        # 今天已有真实行动（StreakRecord）→ 不打扰
        active_today = (
            db.query(StreakRecord)
            .filter(
                StreakRecord.user_id == user_id,
                StreakRecord.activity_date == day,
            )
            .first()
        )
        if active_today is not None:
            continue

        # 今天已发过 reminder → 同一天最多 1 条
        already_sent = (
            db.query(Notification)
            .filter(
                Notification.user_id == user_id,
                Notification.type == "reminder",
                Notification.created_at >= datetime.combine(day, time.min, tzinfo=REMINDER_TZ),
                Notification.created_at < datetime.combine(
                    day + timedelta(days=1), time.min, tzinfo=REMINDER_TZ
                ),
            )
            .first()
        )
        if already_sent is not None:
            continue

        result.append(user_id)

    return result


async def send_d2_reminders(db: Session | None = None) -> int:
    """给筛选出的用户逐个发送 reminder，返回发送条数。"""
    from app.api.notifications import push_notification
    from app.database import SessionLocal

    owned = False
    if db is None:
        db = SessionLocal()
        owned = True
    try:
        user_ids = find_d2_reminder_users(db)
        sent = 0
        for user_id in user_ids:
            try:
                await push_notification(
                    db,
                    user_id,
                    type="reminder",
                    title=REMINDER_TITLE,
                    content=REMINDER_CONTENT,
                )
                sent += 1
            except Exception:
                logger.exception("发送中断次日提醒失败 user_id=%s", user_id)
        if sent:
            logger.info("中断次日提醒已发送 %d 条", sent)
        return sent
    finally:
        if owned:
            db.close()


def register_d2_reminder_job() -> None:
    """startup 注册每日 21:00（北京时间，显式 timezone）提醒 job。

    幂等范式与 seed_default_schedules 一致：已存在的 job 跳过。
    - 开关 MICRO_ACTION_REMINDER_D2 默认 False，关闭时不注册；
    - ENVIRONMENT == "test" 时不注册（测试环境不触发真实 job）。
    """
    if not settings.MICRO_ACTION_REMINDER_D2:
        logger.info("MICRO_ACTION_REMINDER_D2 未开启，跳过中断次日提醒 job 注册")
        return
    if settings.ENVIRONMENT == "test":
        logger.info("测试环境不注册中断次日提醒 job")
        return

    from app.api.crawlers import get_scheduler

    scheduler = get_scheduler()
    if not scheduler:
        logger.warning("APScheduler 未可用，跳过中断次日提醒 job 注册")
        return

    if scheduler.get_job(REMINDER_JOB_ID):
        return

    scheduler.add_job(
        _run_d2_reminder_job,
        "cron",
        id=REMINDER_JOB_ID,
        replace_existing=True,
        hour=21,
        minute=0,
        timezone=REMINDER_TZ,
    )
    logger.info("已注册中断次日提醒 job: 每日 21:00（Asia/Shanghai）")


async def _run_d2_reminder_job() -> None:
    """APScheduler 回调：自建 DB 会话执行提醒发送。"""
    try:
        await send_d2_reminders()
    except Exception:
        logger.exception("中断次日提醒 job 执行失败")


__all__ = [
    "REMINDER_JOB_ID",
    "REMINDER_TZ",
    "find_d2_reminder_users",
    "send_d2_reminders",
    "register_d2_reminder_job",
]
