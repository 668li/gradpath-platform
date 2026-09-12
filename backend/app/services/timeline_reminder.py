"""考公时间线提醒引擎（feature 001 / M3）— D2 单点闸 + D4 幂等 + D5 提前量表。

宪法 4 的机器闸在此：``pick_template`` 是文案模板唯一入口——
断言类措辞（"明天截止/已发布/今天"）仅当节点 date_status==OFFICIAL 才允许；
PREDICTED 一律降级为试探类（"预计…建议收藏官方入口，公告后自动更新"）。
测试断言打到**最终渲染字符串**（test_predicted_node_never_assertive_copy）。

幂等：写 t_timeline_reminder_log 撞 unique(user,node,kind) → 跳过（D4，DB 硬闸）。
配额：试探类（=INFO 级）Server 酱每人每日 ≤3（运维侧 sec_watcher 同口径）；
断言类不受限。站内 Notification 恒发（配额只挡 Server 酱通道）。
调度：进程内 APScheduler 日扫 07:30（Asia/Shanghai），复用 d2 先例注册。
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.core.push_notify import send_serverchan
from app.models.exam_timeline import (
    DateStatus,
    Exam,
    ExamNode,
    ExamSubscription,
    NodeStage,
    ReminderKind,
    ReminderTone,
    TimelineReminderLog,
)
from app.utils.business_time import BEIJING_TZ, beijing_today

logger = logging.getLogger(__name__)

TIMELINE_JOB_ID = "timeline_reminder_daily"
REMINDER_TZ = BEIJING_TZ

# 试探类 Server 酱每人每日配额（INFO 口径，对齐宪法 6 / FR4）
TENTATIVE_SERVERCHAN_DAILY_QUOTA = 3

# 断言词表——负例测试用，PREDICTED 节点的最终文案绝不允许出现任何一词
ASSERTIVE_WORDS = ("明天", "今天", "已发布", "已开启", "截止", "取消", "还有", "现在开始")

_ENTRY_HINT = "官方入口：{url}。预测日期，公告后自动更新。"
_NO_ENTRY = "（本场考试暂无可核验来源，官方公告后自动点亮）"


@dataclass(frozen=True)
class ReminderDraft:
    """pick_template 产物——文案已定稿，落库/推送层不得改写（单点闸保证）。"""

    tone: ReminderTone
    title: str
    content: str
    link: str


# ----------------------------------------------------------------------
# D5 提前量表：某节点今天触发哪些 kind
# ----------------------------------------------------------------------


def firing_kinds(node: ExamNode, today: date) -> list[ReminderKind]:
    """UNKNOWN 永不触发；有日期的节点按 D5 表命中。"""
    if node.date_status == DateStatus.UNKNOWN or node.planned_date is None:
        return []
    d = node.planned_date
    end = node.planned_end_date
    kinds: list[ReminderKind] = []
    stage = node.stage_key

    if stage == NodeStage.announce:
        if today == d - timedelta(days=3):
            kinds.append(ReminderKind.heads_up)
        if today == d:
            kinds.append(ReminderKind.opening)
    elif stage == NodeStage.registration:
        if today == d - timedelta(days=3):
            kinds.append(ReminderKind.heads_up)
        if today == d:
            kinds.append(ReminderKind.opening)
        if end and today == end - timedelta(days=1):
            kinds.append(ReminderKind.deadline_t1)
    elif stage == NodeStage.payment:
        target = end or d
        if today == target - timedelta(days=2):
            kinds.append(ReminderKind.deadline_t1)
    elif stage == NodeStage.admission_ticket:
        if today == d:
            kinds.append(ReminderKind.opening)
    elif stage == NodeStage.written:
        if today == d - timedelta(days=7):
            kinds.append(ReminderKind.heads_up)
        if today == d - timedelta(days=1):
            kinds.append(ReminderKind.deadline_t1)
        if today == d:
            kinds.append(ReminderKind.dayof)
    elif stage in (NodeStage.score, NodeStage.adjustment):
        if today == d:
            kinds.append(ReminderKind.opening)
    elif stage in (NodeStage.interview, NodeStage.medical, NodeStage.political):
        if today == d + timedelta(days=1):
            kinds.append(ReminderKind.followup)
    return kinds


# ----------------------------------------------------------------------
# D2 单点闸：kind → (tone, 文案)。PREDICTED ⇒ 断言类强制降级试探。
# ----------------------------------------------------------------------

# "断言类" kind：语义上必须指向确定日期才成立
_ASSERTIVE_KINDS = {
    ReminderKind.opening,
    ReminderKind.deadline_t1,
    ReminderKind.dayof,
    ReminderKind.followup,
}


def pick_template(node: ExamNode, exam: Exam, kind: ReminderKind) -> ReminderDraft:
    """模板唯一选择器（宪法 4 落点）。任何调用方都不得绕过本函数拼文案。

    tone 判定只看一个事实：node.date_status == OFFICIAL。
    PREDICTED/UNKNOWN → 永远试探（UNKNOWN 不会走到这里——firing_kinds 已挡）。
    """
    official = node.date_status == DateStatus.OFFICIAL
    tone = (
        ReminderTone.assertive
        if (kind in _ASSERTIVE_KINDS and official)
        else ReminderTone.tentative
    )

    entry = node.official_entry_url or exam.official_home_url or ""
    link = f"/civil-service?tab=timeline&node={node.id}"
    d = node.planned_date
    end = node.planned_end_date
    ds = d.isoformat() if d else ""

    def tail() -> str:
        if tone == ReminderTone.tentative:
            return _ENTRY_HINT.format(url=entry) if entry else _NO_ENTRY
        return f"（{ds}）官方入口：{entry}" if entry else f"（{ds}）"

    if kind == ReminderKind.heads_up:
        # 预告类措辞本身不含具体日承诺——OFFICIAL 才允许报倒计时天数
        if tone == ReminderTone.assertive and d:
            delta = (d - beijing_today()).days
            head = f"【{exam.name}】{node.title}还有 {delta} 天（{ds}）"
        else:
            head = f"【{exam.name}】{node.title}预计近期开始"
    elif kind == ReminderKind.opening:
        head = (
            f"【{exam.name}】{node.title}已开启"
            if tone == ReminderTone.assertive
            else f"【{exam.name}】{node.title}预计近期开放"
        )
    elif kind == ReminderKind.deadline_t1:
        deadline_txt = (end or d).isoformat() if (end or d) else ""
        head = (
            f"【{exam.name}】{node.title}明天截止（{deadline_txt}）"
            if tone == ReminderTone.assertive
            else f"【{exam.name}】{node.title}窗口预计临近结束，建议今日内确认"
        )
    elif kind == ReminderKind.dayof:
        head = (
            f"【{exam.name}】{node.title}今天举行，按准考证要求入场"
            if tone == ReminderTone.assertive
            else f"【{exam.name}】{node.title}预计临近，请留意准考证安排"
        )
    else:  # followup
        head = (
            f"【{exam.name}】{node.title}已结束，按招录机关通知跟进后续"
            if tone == ReminderTone.assertive
            else f"【{exam.name}】{node.title}预计临近结束，留意官方后续通知"
        )
    return ReminderDraft(tone=tone, title=head, content=head + "。" + tail(), link=link)


# ----------------------------------------------------------------------
# 发送：幂等（D4）→ 配额（FR4）→ 站内 + Server 酱
# ----------------------------------------------------------------------


async def _send_one(
    db: Session,
    user_id: str,
    node: ExamNode,
    exam: Exam,
    kind: ReminderKind,
    draft: ReminderDraft,
    *,
    notify_channels: list[str],
    today: date,
    serverchan_budget_left: int,
) -> bool:
    """写提醒日志（撞唯一键=跳过）→ 站内 Notification → Server 酱（配额内）。"""
    from app.api.notifications import push_notification

    channel = "inapp"
    want_serverchan = "serverchan" in notify_channels
    if want_serverchan:
        if draft.tone == ReminderTone.assertive or serverchan_budget_left > 0:
            channel = "both"
    log = TimelineReminderLog(
        user_id=user_id,
        node_id=str(node.id),
        kind=kind,
        tone=draft.tone,
        sent_at=datetime.now(timezone.utc),
        channel=channel,
    )
    db.add(log)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()  # 撞 unique(user,node,kind)：终身一条（D4）
        return False

    n = await push_notification(
        db,
        uuid.UUID(user_id),
        type="reminder",
        title=draft.title,
        content=draft.content,
        link=draft.link,
    )
    log.notification_id = str(n.id)

    if channel == "both":
        ok = send_serverchan(draft.title, draft.content)
        if not ok:
            logger.warning("Server酱推送失败（不阻塞）user=%s node=%s", user_id, node.id)
    db.commit()
    return True


def _tentative_serverchan_used(db: Session, user_id: str, today: date) -> int:
    day_start = datetime.combine(today, datetime.min.time(), tzinfo=REMINDER_TZ)
    day_end = day_start + timedelta(days=1)
    return (
        db.query(TimelineReminderLog)
        .filter(
            TimelineReminderLog.user_id == user_id,
            TimelineReminderLog.tone == ReminderTone.tentative,
            TimelineReminderLog.channel.in_(["serverchan", "both"]),
            TimelineReminderLog.sent_at >= day_start,
            TimelineReminderLog.sent_at < day_end,
        )
        .count()
    )


async def send_timeline_reminders(db: Session, *, today: date | None = None) -> dict[str, int]:
    """日扫主流程：有效订阅 × 命中窗口节点 → 分级文案 → 幂等+配额 → 双通道。"""
    day = today or beijing_today()
    summary = {"sent": 0, "skipped_dup": 0, "skipped_quota": 0}
    subs = db.query(ExamSubscription).filter(ExamSubscription.notify_channels != []).all()
    for sub in subs:
        user_id = str(sub.user_id)
        exam = sub.exam
        budget_used = _tentative_serverchan_used(db, user_id, day)
        for node in sorted(exam.nodes, key=lambda n: n.node_seq):
            for kind in firing_kinds(node, day):
                draft = pick_template(node, exam, kind)
                quota_left = max(0, TENTATIVE_SERVERCHAN_DAILY_QUOTA - budget_used)
                want_push = "serverchan" in sub.notify_channels
                if want_push and draft.tone == ReminderTone.tentative and quota_left <= 0:
                    # 配额只挡 Server 酱通道；站内照发 → 降级 channels=["inapp"]
                    sub_quota_hit = True
                    channels = ["inapp"]
                else:
                    sub_quota_hit = False
                    channels = list(sub.notify_channels)
                sent = await _send_one(
                    db,
                    user_id,
                    node,
                    exam,
                    kind,
                    draft,
                    notify_channels=channels,
                    today=day,
                    serverchan_budget_left=0 if sub_quota_hit else quota_left,
                )
                if sent:
                    summary["sent"] += 1
                    if sub_quota_hit:
                        summary["skipped_quota"] += 1
                    elif want_push and draft.tone == ReminderTone.tentative:
                        budget_used += 1
                else:
                    summary["skipped_dup"] += 1
    logger.info(
        "时间线提醒扫描完成：sent=%s dup=%s quota=%s",
        summary["sent"],
        summary["skipped_dup"],
        summary["skipped_quota"],
    )
    return summary


async def _run_timeline_job() -> None:
    """APScheduler 回调：自建会话执行扫描。"""
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        await send_timeline_reminders(db)
    except Exception:
        logger.exception("时间线提醒 job 执行失败")
    finally:
        db.close()


def register_timeline_jobs() -> None:
    """startup 注册每日 07:30（Asia/Shanghai）扫描。复刻 d2 先例：开关+测试环境+幂等。"""
    if not settings.TIMELINE_REMINDER_ENABLED:
        logger.info("TIMELINE_REMINDER_ENABLED 未开启，跳过时间线提醒 job 注册")
        return
    if settings.ENVIRONMENT == "test":
        logger.info("测试环境不注册时间线提醒 job")
        return

    from app.api.crawlers import get_scheduler

    scheduler = get_scheduler()
    if not scheduler:
        logger.warning("APScheduler 未可用，跳过时间线提醒 job 注册")
        return
    if scheduler.get_job(TIMELINE_JOB_ID):
        return
    scheduler.add_job(
        _run_timeline_job,
        "cron",
        id=TIMELINE_JOB_ID,
        replace_existing=True,
        hour=7,
        minute=30,
        timezone=REMINDER_TZ,
    )
    logger.info("已注册时间线提醒 job：每日 07:30（Asia/Shanghai）")


__all__ = [
    "TIMELINE_JOB_ID",
    "ASSERTIVE_WORDS",
    "TENTATIVE_SERVERCHAN_DAILY_QUOTA",
    "ReminderDraft",
    "firing_kinds",
    "pick_template",
    "send_timeline_reminders",
    "register_timeline_jobs",
]
