"""证据链硬闸负例测试 — spec §2.5 FR-E1/E2/E5 + 宪法 1/4。

名字可追溯宪法条款：断言的是"造假在构造上不可能"，不是"我记得实现正确"。
所有网络抓取以注入 fetcher 模拟真实 HTTP（含壳页、坏日期、非政府域），
测试环境不依赖外网连通性。
"""

from datetime import date, datetime, timezone

import pytest

from app.models.exam_timeline import DateStatus, EvidenceChannel, Exam, ExamNode, NodeStage
from app.services.timeline_service import (
    EvidenceRejected,
    apply_evidence_date,
    derive_predicted_next_year,
    html_to_text,
    record_manual_paste,
    require_evidence_fetch,
    upsert_skeleton,
    validate_honesty,
)

# ----------------------------------------------------------------------
# fixtures
# ----------------------------------------------------------------------

# 真实公告正文片段（2025年10月15日起报名…），构造 ≥2KB 以越过壳页阈值
_REAL_BODY = (
    "报考者可于2025年10月15日8:00至10月24日18:00期间登录专题网站进行报名并提交报考申请，"
    "每次只能选报1个职位。招录机关于2025年10月15日8:00至10月26日18:00期间对报考申请进行审查。"
    "笔试时间为2025年11月30日。可于2026年1月登录专题网站查询笔试成绩。"
)
_PAD = (
    "<p>中央机关及其直属机构2026年度考试录用公务员公告，根据公务员法和《公务员录用规定》组织实施。</p>"
    * 40
)
_GOOD_HTML = ("<html><body>" + _PAD + "<p>" + _REAL_BODY + "</p></body></html>").encode()
_SHELL_HTML = b"<html><head><title>loading</title></head><body></body></html>"  # <2KB SPA/跳转壳


def _fetch_ok(url):
    return 200, _GOOD_HTML


def _fetch_shell(url):
    return 200, _SHELL_HTML


def _fetch_404(url):
    return 404, b"not found"


@pytest.fixture
def exam(db_session):
    e = Exam(
        code="guokao-2027",
        name="2027 国考",
        track="guokao",
        year=2027,
        official_home_url="http://bm.scs.gov.cn/kl2027",
        status="upcoming",
    )
    db_session.add(e)
    db_session.flush()
    upsert_skeleton(db_session, e)
    db_session.commit()
    return e


# ----------------------------------------------------------------------
# 诚实组合闸（宪法 4 单点校验）
# ----------------------------------------------------------------------


def test_unknown_node_must_not_carry_any_date_or_evidence():
    """UNKNOWN 却带了日期/证据 → 直接拒绝（宁可没数据，不伪装知道）。"""
    with pytest.raises(EvidenceRejected):
        validate_honesty(
            date_status=DateStatus.UNKNOWN,
            planned_date=date(2026, 10, 15),
            planned_end_date=None,
            predict_basis=None,
            source_url=None,
            collected_at=None,
            evidence_id=None,
        )


def test_official_must_carry_source_and_evidence():
    """OFFICIAL 缺 source/evidence → 拒（FR-E1 写入前校验，不留旁路）。"""
    with pytest.raises(EvidenceRejected):
        validate_honesty(
            date_status=DateStatus.OFFICIAL,
            planned_date=date(2026, 10, 15),
            planned_end_date=None,
            predict_basis=None,
            source_url="http://bm.scs.gov.cn",
            collected_at=datetime.now(timezone.utc),
            evidence_id=None,
        )


def test_predicted_must_not_impersonate_official():
    with pytest.raises(EvidenceRejected):
        validate_honesty(
            date_status=DateStatus.PREDICTED,
            planned_date=date(2026, 10, 15),
            planned_end_date=None,
            predict_basis="按 2026 平移",
            source_url="http://bm.scs.gov.cn",  # PREDICTED 不得挂来源
            collected_at=None,
            evidence_id=None,
        )


# ----------------------------------------------------------------------
# fetch 通道三拒（FR-E1 三条件 + FR-E5 负例）
# ----------------------------------------------------------------------


def test_fetch_gate_rejects_non_gov_domain(db_session):
    with pytest.raises(EvidenceRejected):
        require_evidence_fetch(
            db_session, "http://evil.example.com/x", date(2025, 10, 15), fetcher=_fetch_ok
        )


def test_fetch_gate_rejects_shell_page(db_session):
    with pytest.raises(EvidenceRejected):
        require_evidence_fetch(
            db_session,
            "https://www.beijing.gov.cn/x",
            date(2025, 10, 15),
            fetcher=_fetch_shell,
        )


def test_fetch_gate_rejects_404(db_session):
    with pytest.raises(EvidenceRejected):
        require_evidence_fetch(
            db_session, "https://www.beijing.gov.cn/x", date(2025, 10, 15), fetcher=_fetch_404
        )


def test_fetch_gate_rejects_date_not_in_body(db_session):
    """正文真实但不含所写日期 → 拒（防把记忆日期冒充公告日期）。"""
    with pytest.raises(EvidenceRejected):
        require_evidence_fetch(
            db_session,
            "https://www.beijing.gov.cn/x",
            date(2030, 1, 1),
            fetcher=_fetch_ok,
        )


def test_fetch_gate_accepts_evidenced_date_and_records_row(db_session):
    ev = require_evidence_fetch(
        db_session,
        "https://www.beijing.gov.cn/x",
        date(2025, 10, 15),
        fetcher=_fetch_ok,
        recorded_by="test",
    )
    assert ev.channel == EvidenceChannel.fetch
    assert ev.content_sha and len(ev.content_sha) == 64
    assert "2025年10月15日" in ev.matched_excerpt
    db_session.commit()


def test_apply_official_sets_full_honesty_fields(db_session, exam):
    node = next(n for n in exam.nodes if n.stage_key == NodeStage.registration)
    assert node.date_status == DateStatus.UNKNOWN
    ev = apply_evidence_date(
        db_session,
        node,
        on_date=date(2025, 10, 15),
        end_date=date(2025, 10, 24),
        source_url="https://www.beijing.gov.cn/x",
        fetcher=_fetch_ok,
    )
    assert node.date_status == DateStatus.OFFICIAL
    assert node.evidence_id == str(ev.id)
    assert node.source_url and node.collected_at
    assert node.planned_date == date(2025, 10, 15)
    assert node.planned_end_date == date(2025, 10, 24)
    db_session.commit()


def test_official_no_downgrade(db_session, exam):
    """禁 OFFICIAL 回退（回退=数据质量事故）。"""
    node = next(n for n in exam.nodes if n.stage_key == NodeStage.written)
    apply_evidence_date(
        db_session,
        node,
        on_date=date(2025, 11, 30),
        source_url="https://www.beijing.gov.cn/x",
        fetcher=_fetch_ok,
    )
    # 试图从 OFFICIAL 降级到 PREDICTED 由 derive 触发——应被拒
    node.date_status = DateStatus.OFFICIAL
    with pytest.raises(EvidenceRejected):
        from app.services.timeline_service import _check_transition

        _check_transition(DateStatus.OFFICIAL, DateStatus.PREDICTED)
    db_session.commit()


# ----------------------------------------------------------------------
# manual_paste 通道（FR-E2）
# ----------------------------------------------------------------------


def test_manual_paste_requires_date_in_pasted_text(db_session):
    with pytest.raises(EvidenceRejected):
        record_manual_paste(
            db_session,
            "https://www.beijing.gov.cn/x",
            date(2031, 5, 5),
            pasted_text="这是一段根本没有该日期的正文" + _PAD,
            recorded_by="user@example.com",
        )


def test_manual_paste_accepts_and_archives_full_text(db_session):
    pasted = _PAD + _REAL_BODY  # ≥2KB 的公告原文
    ev = record_manual_paste(
        db_session,
        "https://www.beijing.gov.cn/x",
        date(2025, 10, 15),
        pasted_text=pasted,
        recorded_by="user@example.com",
    )
    assert ev.channel == EvidenceChannel.manual_paste
    assert ev.pasted_text == pasted  # 全量原文留档可审计（FR-E2）


# ----------------------------------------------------------------------
# FR-E6 预测锚点链（09-12 二次修订核心）
# ----------------------------------------------------------------------


def test_predict_requires_prev_year_evidence(db_session, exam):
    """2027 无 2026 已证同环节日期时，derive 不得产生任何 PREDICTED（链断=UNKNOWN）。"""
    prev = Exam(
        code="guokao-2026",
        name="2026 国考",
        track="guokao",
        year=2026,
        official_home_url="http://bm.scs.gov.cn/kl2026",
        status="closed",
    )
    db_session.add(prev)
    db_session.flush()
    upsert_skeleton(db_session, prev)
    db_session.commit()

    # 2026 registration 保持 UNKNOWN（无证据）→ 2027 derive 不得写 PREDICTED
    changed = derive_predicted_next_year(db_session, exam, prev)
    assert changed == 0
    for n in exam.nodes:
        assert n.date_status == DateStatus.UNKNOWN


def test_predict_derives_next_year_only_for_evidenced_stages(db_session):
    """2026 有证据的环节 → 2027 平移一年 PREDICTED；无证据环节仍 UNKNOWN。"""
    e26 = Exam(
        code="guokao-2026",
        name="2026 国考",
        track="guokao",
        year=2026,
        official_home_url="http://bm.scs.gov.cn/kl2026",
        status="closed",
    )
    e27 = Exam(
        code="guokao-2027",
        name="2027 国考",
        track="guokao",
        year=2027,
        official_home_url="http://bm.scs.gov.cn/kl2027",
        status="upcoming",
    )
    db_session.add_all([e26, e27])
    db_session.flush()
    upsert_skeleton(db_session, e26)
    upsert_skeleton(db_session, e27)

    reg26 = next(n for n in e26.nodes if n.stage_key == NodeStage.registration)
    apply_evidence_date(
        db_session,
        reg26,
        on_date=date(2025, 10, 15),
        end_date=date(2025, 10, 24),
        source_url="https://www.beijing.gov.cn/x",
        fetcher=_fetch_ok,
    )
    changed = derive_predicted_next_year(db_session, e27, e26)
    reg27 = next(n for n in e27.nodes if n.stage_key == NodeStage.registration)
    assert reg27.date_status == DateStatus.PREDICTED
    assert reg27.planned_date == date(2026, 10, 15)
    assert reg27.planned_end_date == date(2026, 10, 24)
    assert "2026" in reg27.predict_basis
    # 无证据环节（如 hire）2027 仍 UNKNOWN
    hire27 = next(n for n in e27.nodes if n.stage_key == NodeStage.hire)
    assert hire27.date_status == DateStatus.UNKNOWN
    assert changed == 1
    db_session.commit()


# ----------------------------------------------------------------------
# seed 幂等 + 零日期常量负断言（FR-E3/E4 + quickstart §1）
# ----------------------------------------------------------------------


def test_seed_is_idempotent_and_keeps_zero_dates_without_evidence(db_session):
    from app.seed.seed_exam_timeline import seed_exam_timeline

    summary1 = seed_exam_timeline(db_session)
    n_nodes = db_session.query(ExamNode).count()
    summary2 = seed_exam_timeline(db_session)
    # 跑两遍计数不变
    assert db_session.query(ExamNode).count() == n_nodes
    assert summary2["official_without_evidence"] == 0
    # 无提案时全部 UNKNOWN，OFFICIAL=0；骨架规模=3 考次×12 环节 + kaoyan-2027×8 环节（B2）
    assert summary1["proposal"] == {"ok": [], "rejected": []}
    assert len(summary1["exams"]) == 4
    assert n_nodes == 44
    assert db_session.query(ExamNode).filter_by(date_status=DateStatus.OFFICIAL).count() == 0


def test_seed_proposal_rejection_is_audited_not_silent(db_session):
    """坏提案（日期不在正文）→ 进 rejected 报告且节点保持 UNKNOWN，绝不静默写 OFFICIAL。"""
    from app.seed.seed_exam_timeline import seed_exam_timeline

    proposals = [
        {
            "exam": "guokao-2026",
            "stage_key": "registration",
            "date": "2099-01-01",  # 正文绝无此日期
            "url": "https://www.beijing.gov.cn/x",
        }
    ]
    summary = seed_exam_timeline(db_session, proposals=proposals, fetcher=_fetch_ok)
    assert summary["proposal"]["rejected"]
    assert not summary["proposal"]["ok"]
    assert summary["official_without_evidence"] == 0


def test_seed_with_proposal_is_idempotent_across_runs(db_session):
    """提案 seed 跑两遍：节点日期/证据行数不变（幂等短路复用证据，quickstart §1）。"""
    from app.models.exam_timeline import TimelineEvidence
    from app.seed.seed_exam_timeline import seed_exam_timeline

    proposals = [
        {
            "exam": "guokao-2026",
            "stage_key": "registration",
            "date": "2025-10-15",
            "end_date": "2025-10-24",
            "url": "https://www.beijing.gov.cn/x",
        }
    ]
    seed_exam_timeline(db_session, proposals=proposals, fetcher=_fetch_ok)
    ev_count = db_session.query(TimelineEvidence).count()
    nodes = db_session.query(ExamNode).count()
    summary = seed_exam_timeline(db_session, proposals=proposals, fetcher=_fetch_ok)
    assert db_session.query(TimelineEvidence).count() == ev_count
    assert db_session.query(ExamNode).count() == nodes
    assert summary["official_without_evidence"] == 0


def test_seed_proposal_good_writes_official_and_predicts_2027(db_session):
    from app.seed.seed_exam_timeline import seed_exam_timeline

    proposals = [
        {
            "exam": "guokao-2026",
            "stage_key": "registration",
            "date": "2025-10-15",
            "end_date": "2025-10-24",
            "url": "https://www.beijing.gov.cn/x",
        }
    ]
    summary = seed_exam_timeline(db_session, proposals=proposals, fetcher=_fetch_ok)
    assert summary["proposal"]["ok"]
    assert summary["official_without_evidence"] == 0
    reg27 = (
        db_session.query(ExamNode)
        .join(Exam)
        .filter(Exam.code == "guokao-2027", ExamNode.stage_key == NodeStage.registration)
        .first()
    )
    assert reg27.date_status == DateStatus.PREDICTED
    assert reg27.planned_date == date(2026, 10, 15)


def test_html_to_text_decodes_and_strips():
    # &#21313;&#26376; = 十月；script 块整体剔除，实体解码
    raw = b"<html><body>&#21313;&#26376; <script>var x=', ';</script></body></html>"
    assert html_to_text(raw) == "十月"
