"""speckit 003 负例测试——记忆感 / 行动钩子 / 推送深链三件套。

负例穿到最终产物（宪法 4 判卷惯例，防假绿）：
- 沉淀块空 ⇒ apply_sedimentation 只挂"禁虚构"行（确定性面，LLM 行为靠冒烟）
- 钩子"已做过"不重复推销；异常 ⇒ 空表
- PREDICTED 节点深链 prefill 解码后不命中 ASSERTIVE_WORDS 任一禁词
"""

import logging
from datetime import date, datetime, timezone
from uuid import uuid4

from app.config import settings
from app.models.exam_timeline import (
    DateStatus,
    Exam,
    ExamNode,
    ExamSubscription,
    NodeFeedback,
    NodeFeedbackStatus,
    NodeStage,
    ReminderKind,
    ReminderTone,
    TimelineReminderLog,
)
from app.models.micro_action import MicroActionPlan, MicroActionTask
from app.models.user import User
from app.services import chat_deep_link as cdl
from app.services.action_hook_service import build_action_hooks
from app.services.chat_service import MEMORY_DISCIPLINE, NO_SEDIMENT_DISCIPLINE, apply_sedimentation
from app.services.sedimentation_service import build_sedimentation_block
from app.services.timeline_reminder import ASSERTIVE_WORDS

# 静音服务层降级 debug 日志（测试里故意造异常，别刷屏）
logging.getLogger("app.services").setLevel(logging.WARNING)


# ---------------------------------------------------------------- 夹具


def _make_user(db, email="stick@example.com") -> User:
    u = User(email=email, password_hash="x", name="粘性测试")
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _make_exam_node(
    db,
    *,
    date_status=DateStatus.PREDICTED,
    stage=NodeStage.registration,
    planned=date(2026, 10, 20),
):
    exam = Exam(
        code=f"test-gk-{uuid4().hex[:6]}",
        name="测试国考 2027",
        track="guokao",
        year=2027,
        status="upcoming",
    )
    db.add(exam)
    db.flush()
    node = ExamNode(
        exam_id=exam.id,
        stage_key=stage,
        node_seq=3,
        title="网上报名",
        date_status=date_status,
        planned_date=planned,
        predict_basis="测试锚点（测试夹具）" if date_status == DateStatus.PREDICTED else None,
    )
    db.add(node)
    db.commit()
    return exam, node


def _subscribe(db, user, exam):
    sub = ExamSubscription(user_id=str(user.id), exam_id=exam.id)
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub


def _log_reminder(db, user, node, kind=ReminderKind.opening):
    log = TimelineReminderLog(
        user_id=str(user.id),
        node_id=str(node.id),
        kind=kind,
        tone=ReminderTone.tentative,
        sent_at=datetime.now(timezone.utc),
        channel="inapp",
    )
    db.add(log)
    db.commit()
    return log


def _make_micro_plan(db, user, *, with_pending_task=True):
    plan = MicroActionPlan(user_id=user.id, target_path="employment", status="active")
    db.add(plan)
    db.flush()
    if with_pending_task:
        db.add(
            MicroActionTask(
                plan_id=plan.id,
                day_number=2,
                task_type="research",
                title="查 3 个目标 JD",
                description="描述",
                estimated_minutes=20,
                status="pending",
            )
        )
    db.commit()
    return plan


# ---------------------------------------------------------------- 记忆感（FR1）


def test_sedimentation_empty_for_new_user(db_session):
    """无沉淀用户 ⇒ 块为空串（ Constitution 1：一个字不得编）。"""
    user = _make_user(db_session, "sed-empty@example.com")
    assert build_sedimentation_block(db_session, user.id) == ""


def test_apply_sedimentation_empty_state(db_session):
    """块空 ⇒ 只追加"禁虚构"纪律行，不得出现沉淀块头。"""
    out = apply_sedimentation("【用户画像】X", "")
    assert NO_SEDIMENT_DISCIPLINE in out
    assert MEMORY_DISCIPLINE not in out
    assert "【用户沉淀" not in out


def test_apply_sedimentation_with_block_state(db_session):
    """块非空 ⇒ 块+记忆感纪律都在，且原文原样保留。"""
    out = apply_sedimentation(
        "【用户画像】X",
        "【用户沉淀（真实库数据，引用必须与此一致，禁止编造）】\n- 已订阅考次：国考 2027",
    )
    assert MEMORY_DISCIPLINE in out
    assert "- 已订阅考次：国考 2027" in out


def test_sedimentation_block_contains_subscription(db_session):
    user = _make_user(db_session, "sed-sub@example.com")
    exam, _ = _make_exam_node(db_session)
    _subscribe(db_session, user, exam)
    block = build_sedimentation_block(db_session, user.id)
    assert "已订阅考次" in block
    assert exam.name in block


def test_sedimentation_pending_feedback_disappears_after_feedback(db_session):
    """已发提醒无回传 ⇒ 待回传行出现；回传后 ⇒ 消失（三态诚实的库事实面）。"""
    user = _make_user(db_session, "sed-pending@example.com")
    exam, node = _make_exam_node(db_session)
    sub = _subscribe(db_session, user, exam)
    _log_reminder(db_session, user, node)

    block = build_sedimentation_block(db_session, user.id)
    assert "待回传节点" in block
    assert node.title in block

    db_session.add(
        NodeFeedback(
            subscription_id=sub.id,
            node_id=node.id,
            status=NodeFeedbackStatus.done,
            feedback_at=datetime.now(timezone.utc),
        )
    )
    db_session.commit()
    assert "待回传节点" not in build_sedimentation_block(db_session, user.id)


# ---------------------------------------------------------------- 行动钩子（FR2/FR3/FR7）


def test_hooks_unsubscribed_timeline_question_gives_subscribe(db_session):
    user = _make_user(db_session, "hook-sub@example.com")
    _make_exam_node(db_session)  # 站内有 upcoming 考次
    hooks = build_action_hooks(db_session, user.id, "国考报名时间是什么时候？")
    assert any(h["type"] == "subscribe_timeline" for h in hooks)
    assert len(hooks) <= 2


def test_hooks_subscribed_user_not_pushed_subscribe(db_session):
    """已做过不重复推销（FR3）：已订阅 ⇒ 无订阅钩子。"""
    user = _make_user(db_session, "hook-done@example.com")
    exam, _ = _make_exam_node(db_session)
    _subscribe(db_session, user, exam)
    hooks = build_action_hooks(db_session, user.id, "国考报名什么时候截止？")
    assert not any(h["type"] == "subscribe_timeline" for h in hooks)


def test_hooks_pending_feedback_hook_targets_node(db_session):
    user = _make_user(db_session, "hook-fb@example.com")
    exam, node = _make_exam_node(db_session)
    _subscribe(db_session, user, exam)
    _log_reminder(db_session, user, node)
    hooks = build_action_hooks(db_session, user.id, "国考报名时间是什么时候？")
    fb = [h for h in hooks if h["type"] == "feedback_node"]
    assert fb and f"/civil-service?tab=timeline&node={node.id}" == fb[0]["link"]


def test_hooks_micro_checkin_for_active_plan(db_session):
    user = _make_user(db_session, "hook-micro@example.com")
    _make_micro_plan(db_session, user)
    hooks = build_action_hooks(db_session, user.id, "帮我看看就业前景怎么样")
    assert any(h["type"] == "micro_checkin" for h in hooks)


def test_hooks_explore_when_no_sediment(db_session):
    """无沉淀 + 无数据意图 ⇒ 探索型钩子（不锁赛道）。"""
    user = _make_user(db_session, "hook-explore@example.com")
    hooks = build_action_hooks(db_session, user.id, "你好呀")
    assert hooks and all(h["type"] == "explore" for h in hooks)
    assert len(hooks) <= 2


def test_hooks_capped_at_two(db_session):
    """沉淀拉满（未订阅+待回传+微行动）⇒ 仍 ≤2（FR7 防膨胀）。"""
    user = _make_user(db_session, "hook-cap@example.com")
    exam, node = _make_exam_node(db_session)
    _make_micro_plan(db_session, user)
    _log_reminder(db_session, user, node)  # 无订阅但有待回传（log 不要求订阅行）
    hooks = build_action_hooks(db_session, user.id, "国考报名时间是什么时候？")
    assert len(hooks) <= 2


def test_hooks_degrade_to_empty_on_error(db_session, monkeypatch):
    """FR7 降级负例：钩子服务内部异常 ⇒ 空表，绝不阻塞回答。"""
    user = _make_user(db_session, "hook-degrade@example.com")

    def _boom(*a, **k):
        raise RuntimeError("boom")

    from app.services import action_hook_service

    monkeypatch.setattr(action_hook_service, "_detect_domains", _boom)
    assert build_action_hooks(db_session, user.id, "国考报名什么时候截止？") == []


# ---------------------------------------------------------------- 深链（FR4/FR6）


def test_deeplink_tentative_never_contains_assertive_words(db_session):
    """宪法 4 负例：PREDICTED 节点（tentative tone）的 prefill 解码后
    不命中 ASSERTIVE_WORDS 任一禁词——穿到最终 URL 产物。"""
    from urllib.parse import parse_qs, urlparse

    exam, node = _make_exam_node(db_session, date_status=DateStatus.PREDICTED)
    for kind in ReminderKind:
        link = cdl.build_chat_deep_link(node, exam, kind, ReminderTone.tentative)
        prefill = parse_qs(urlparse(link).query)["prefill"][0]
        for word in ASSERTIVE_WORDS:
            assert word not in prefill, f"kind={kind} prefill 命中禁词「{word}」: {prefill}"


def test_deeplink_official_allows_assertive(db_session):
    """OFFICIAL + 断言 kind ⇒ 直陈式可用（正例，闸只拦预测）。"""
    exam, node = _make_exam_node(db_session, date_status=DateStatus.OFFICIAL)
    link = cdl.build_chat_deep_link(node, exam, ReminderKind.deadline_t1, ReminderTone.assertive)
    from urllib.parse import parse_qs, urlparse

    prefill = parse_qs(urlparse(link).query)["prefill"][0]
    assert "明天截止" in prefill


def test_deeplink_length_cap(db_session):
    """容量硬闸：link 恒 ≤500（Notification.link String(500)）。"""
    exam, node = _make_exam_node(db_session)
    node.title = "超长节点标题" * 20  # 造超长 prefill 源
    for kind in ReminderKind:
        for tone in ReminderTone:
            link = cdl.build_chat_deep_link(node, exam, kind, tone)
            assert len(link) <= 500, f"kind={kind} tone={tone} link 超容量: {len(link)}"
            assert link.startswith("/chat?prefill=")


def test_with_chat_link_no_base_returns_content(monkeypatch):
    monkeypatch.setattr(settings, "SITE_BASE_URL", "")
    assert cdl.with_chat_link("正文", "/chat?x=1") == "正文"


def test_with_chat_link_appends_absolute_url(monkeypatch):
    monkeypatch.setattr(settings, "SITE_BASE_URL", "https://quxianglab.cn/")
    out = cdl.with_chat_link("正文", "/chat?prefill=a")
    assert "正文" in out
    assert "https://quxianglab.cn/chat?prefill=a" in out
