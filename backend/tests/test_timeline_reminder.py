"""M3 提醒引擎测试 — 宪法 4 判卷（quickstart §3 点名的三个测试名）。

核心不是"job 会发提醒"，而是"任何路径都造不出 PREDICTED→断言文案"——
断言打到**最终落库的 Notification 字符串**（负例穿到渲染层，防假绿）。
"""

from datetime import date, timedelta

from app.config import settings
from app.models.exam_timeline import (
    DateStatus,
    Exam,
    ExamNode,
    NodeStage,
    ReminderTone,
    TimelineReminderLog,
)
from app.models.notification import Notification
from app.models.user import User
from app.services import timeline_reminder as tr
from app.services import timeline_service as tl


def _make_user(db, email="tl@example.com") -> User:
    u = User(email=email, password_hash="x", name="时间线测试")
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _seed_exams(db):
    from app.seed.seed_exam_timeline import seed_exam_timeline

    seed_exam_timeline(db)
    return {e.code: e for e in db.query(Exam).all()}


def _set_predicted(node: ExamNode, d: date, *, end: date | None = None):
    """测试内直造 PREDICTED 锚点（等价 derive 产物；避开真实 fetch）。"""
    node.date_status = DateStatus.PREDICTED
    node.planned_date = d
    node.planned_end_date = end
    node.predict_basis = "测试锚点：按上一年已证日期平移（测试夹具）"
    node.source_url = None
    node.collected_at = None
    node.evidence_id = None
    tl.validate_honesty(
        date_status=node.date_status,
        planned_date=node.planned_date,
        planned_end_date=node.planned_end_date,
        predict_basis=node.predict_basis,
        source_url=node.source_url,
        collected_at=node.collected_at,
        evidence_id=node.evidence_id,
    )


# ---------------------------------------------------------------- 1 断言闸


async def test_predicted_node_never_assertive_copy(db_session, monkeypatch):
    """PREDICTED 节点时间窗命中 → 落库文案必须零断言词、只含试探词（宪法 4）。"""
    user = _make_user(db_session)
    exams = _seed_exams(db_session)
    e27 = exams["guokao-2027"]
    announce = next(n for n in e27.nodes if n.stage_key == NodeStage.announce)
    _set_predicted(announce, tr.beijing_today())
    tl.subscribe(db_session, user.id, "guokao-2027")

    monkeypatch.setattr(tr, "send_serverchan", lambda *a, **k: True)
    summary = await tr.send_timeline_reminders(db_session)
    assert summary["sent"] == 1

    n = db_session.query(Notification).order_by(Notification.created_at.desc()).first()
    assert n is not None and n.type == "reminder"
    final_text = n.title + n.content
    for w in tr.ASSERTIVE_WORDS:
        assert w not in final_text, f"PREDICTED 文案出现断言词 {w!r}：{final_text}"
    assert "预计" in final_text and "公告后自动更新" in final_text

    log = db_session.query(TimelineReminderLog).one()
    assert log.tone == ReminderTone.tentative


async def test_official_node_allows_assertive_copy(db_session, monkeypatch):
    """闸的正向半边：OFFICIAL（带真证据）节点允许"已开启"式断言。"""
    user = _make_user(db_session)
    exams = _seed_exams(db_session)
    e26 = exams["guokao-2026"]
    today = tr.beijing_today()

    body = (
        "<html><body><p>中央机关及其直属机构2026年度考试录用公务员公告。</p>" * 30
        + f"<p>公告已于{today.isoformat()}发布，报考者可登录专题网站报名。</p></body></html>"
    ).encode()
    ann26 = next(n for n in e26.nodes if n.stage_key == NodeStage.announce)
    tl.apply_evidence_date(
        db_session,
        ann26,
        on_date=today,
        source_url="https://www.beijing.gov.cn/x",
        fetcher=lambda url: (200, body),
    )
    db_session.commit()

    tl.subscribe(db_session, user.id, "guokao-2026")
    monkeypatch.setattr(tr, "send_serverchan", lambda *a, **k: True)
    summary = await tr.send_timeline_reminders(db_session)
    assert summary["sent"] == 1
    n = db_session.query(Notification).one()
    assert "已发布" in (n.title + n.content) or "已开启" in (n.title + n.content)
    log = db_session.query(TimelineReminderLog).one()
    assert log.tone == ReminderTone.assertive


async def test_unknown_node_never_fires(db_session):
    """UNKNOWN（无日期）节点任何窗口都不触发——不排程就不可能提醒。"""
    exams = _seed_exams(db_session)
    for n in exams["guangdong-shengkao-2026"].nodes:
        assert n.date_status == DateStatus.UNKNOWN
        assert tr.firing_kinds(n, tr.beijing_today()) == []


# ---------------------------------------------------------------- 2 幂等


async def test_idempotent_reminder_log(db_session, monkeypatch):
    """job 连跑两次 → 每 (user,node,kind) 恰 1 行（D4 DB 硬闸，非代码 set）。"""
    user = _make_user(db_session)
    exams = _seed_exams(db_session)
    e27 = exams["guokao-2027"]
    reg = next(n for n in e27.nodes if n.stage_key == NodeStage.registration)
    _set_predicted(reg, tr.beijing_today(), end=tr.beijing_today() + timedelta(days=9))
    tl.subscribe(db_session, user.id, "guokao-2027")

    monkeypatch.setattr(tr, "send_serverchan", lambda *a, **k: True)
    s1 = await tr.send_timeline_reminders(db_session)
    s2 = await tr.send_timeline_reminders(db_session)
    assert s1["sent"] == 1
    assert s2["sent"] == 0 and s2["skipped_dup"] == 1
    rows = db_session.query(TimelineReminderLog).all()
    assert len(rows) == 1
    # 站内通知也恰 1 条（幂等挡住第二遍才不发通知）
    assert db_session.query(Notification).count() == 1


# ---------------------------------------------------------------- 3 配额


async def test_info_quota_respected(db_session, monkeypatch):
    """试探类（=INFO）Server 酱每人每日 ≤3：第 4 条只落站内，不发 push。"""
    user = _make_user(db_session)
    exams = _seed_exams(db_session)
    e27 = exams["guokao-2027"]
    today = tr.beijing_today()
    # 4 个试探类命中：announce 当天 / registration T-3 / payment 截止 T-2 / written T-7
    _set_predicted(next(n for n in e27.nodes if n.stage_key == NodeStage.announce), today)
    _set_predicted(
        next(n for n in e27.nodes if n.stage_key == NodeStage.registration),
        today + timedelta(days=3),
    )
    _set_predicted(
        next(n for n in e27.nodes if n.stage_key == NodeStage.payment),
        today + timedelta(days=1),
        end=today + timedelta(days=2),
    )
    _set_predicted(
        next(n for n in e27.nodes if n.stage_key == NodeStage.written), today + timedelta(days=7)
    )
    tl.subscribe(db_session, user.id, "guokao-2027")

    calls = []
    monkeypatch.setattr(tr, "send_serverchan", lambda t, d: calls.append(t) or True)
    summary = await tr.send_timeline_reminders(db_session)
    assert summary["sent"] == 4
    assert len(calls) == tr.TENTATIVE_SERVERCHAN_DAILY_QUOTA == 3
    assert summary["skipped_quota"] == 1
    assert db_session.query(Notification).count() == 4  # 站内全发（配额只挡 push）
    both = db_session.query(TimelineReminderLog).filter_by(channel="both").count()
    assert both == 3


# ---------------------------------------------------------------- 注册闸


def test_no_job_registration_when_flag_off_or_test_env(monkeypatch):
    """开关关闭 / 测试环境不得注册真实 job（d2 同款先例）。"""
    calls = []
    import app.api.crawlers as crawlers

    monkeypatch.setattr(crawlers, "get_scheduler", lambda: calls.append(1))
    monkeypatch.setattr(settings, "TIMELINE_REMINDER_ENABLED", False)
    tr.register_timeline_jobs()
    assert calls == []
    monkeypatch.setattr(settings, "TIMELINE_REMINDER_ENABLED", True)
    monkeypatch.setattr(settings, "ENVIRONMENT", "test")
    tr.register_timeline_jobs()
    assert calls == []
