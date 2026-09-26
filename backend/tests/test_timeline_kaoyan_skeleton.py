# backend/tests/test_timeline_kaoyan_skeleton.py
"""B2（2026-09-26 考研时间线重建）：kaoyan track 骨架与证据提案。

- 骨架按 track 选择：kaoyan=8 环节考研版，guokao 仍 12 环节
- 考研骨架零日期字面量（FR-E3 宪法不变）
- 提案过闸：正文含目标日期（中文格式）→ OFFICIAL+证据行；无日期→ EvidenceRejected
"""

from datetime import date

import pytest

from app.models.exam_timeline import DateStatus, Exam, NodeStage
from app.services.timeline_service import (
    EvidenceRejected,
    SKELETON_12,
    SKELETON_KAOYAN,
    apply_evidence_date,
    upsert_skeleton,
)

# 研招网/教育部规定正文的中文日期写法（省略年份+全形），构造 ≥2KB 越过壳页阈值
_KAOYAN_BODY = (
    "<p>教育部关于印发《2027年全国硕士研究生招生工作管理规定》的通知，"
    "各硕士研究生招生单位：为做好2027年全国硕士研究生考试招生工作，现将有关规定印发给你们。"
    "网上预报名时间为2026年10月9日至10月12日，每日9:00—22:00。"
    "网上报名时间为2026年10月15日至10月24日，每日9:00—22:00。"
    "初试时间为2026年12月19日至20日，超过3小时的考试科目在12月21日举行。</p>" + "<p>各省级教育招生考试机构、各招生单位要高度重视，精心组织，确保研究生招生工作安全顺利。</p>" * 30
)


def _make_exam(db_session, track: str, code: str) -> Exam:
    e = Exam(
        code=code,
        name=f"{code} 测试",
        track=track,
        year=2027,
        official_home_url="https://yz.chsi.com.cn/",
        status="upcoming",
    )
    db_session.add(e)
    db_session.flush()
    upsert_skeleton(db_session, e)
    db_session.commit()
    db_session.expire(e, ["nodes"])
    return e


def test_kaoyan_skeleton_8_stages(db_session):
    assert len(SKELETON_KAOYAN) == 8
    e = _make_exam(db_session, "kaoyan", "kaoyan-test-1")
    stages = [n.stage_key for n in e.nodes]
    assert NodeStage.announce in stages and NodeStage.written in stages
    assert NodeStage.medical not in stages and NodeStage.political not in stages
    first = e.nodes[0]
    assert first.title == "招生管理规定发布"
    # 宪法：骨架节点全部 UNKNOWN（日期只能来自证据通道）
    assert all(n.date_status == DateStatus.UNKNOWN for n in e.nodes)


def test_guokao_skeleton_unchanged(db_session):
    assert len(SKELETON_12) == 12
    e = _make_exam(db_session, "guokao", "guokao-test-1")
    assert len(e.nodes) == 12


def _fetch_kaoyan(url):
    return 200, _KAOYAN_BODY.encode()


def test_kaoyan_proposal_official(db_session):
    """正文含中文日期 → 提案过闸写 OFFICIAL+证据（模拟 moe.gov.cn 规定原文页）。"""
    e = _make_exam(db_session, "kaoyan", "kaoyan-test-2")
    node = next(n for n in e.nodes if n.stage_key == NodeStage.registration)
    apply_evidence_date(
        db_session,
        node,
        on_date=date(2026, 10, 15),
        end_date=date(2026, 10, 24),
        source_url="http://www.moe.gov.cn/srcsite/A15/moe_778/s3261/202609/t20260923_1451734.html",
        recorded_by="test-b2",
        fetcher=_fetch_kaoyan,
    )
    db_session.commit()
    assert node.date_status == DateStatus.OFFICIAL
    assert node.planned_date == date(2026, 10, 15)
    assert node.planned_end_date == date(2026, 10, 24)
    assert node.evidence_id is not None


def test_kaoyan_proposal_rejects_missing_date(db_session):
    """正文无目标日期 → 拒写（宁可 UNKNOWN 不编造）。"""
    e = _make_exam(db_session, "kaoyan", "kaoyan-test-3")
    node = next(n for n in e.nodes if n.stage_key == NodeStage.written)

    body = "<p>教育部部署考试招生工作。</p>" * 80
    with pytest.raises(EvidenceRejected):
        apply_evidence_date(
            db_session,
            node,
            on_date=date(2026, 12, 19),
            end_date=date(2026, 12, 20),
            source_url="http://www.moe.gov.cn/srcsite/A15/moe_778/s3261/202609/t20260923_1451734.html",
            recorded_by="test-b2",
            fetcher=lambda url: (200, body.encode()),
        )
    db_session.rollback()
    assert node.date_status == DateStatus.UNKNOWN
