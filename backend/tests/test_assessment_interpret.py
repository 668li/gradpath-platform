# backend/tests/test_assessment_interpret.py
"""interpret 接线测试 — 同分人群去向使用用户自己真实回传分。

覆盖（任务书任务 1）：
- 用户在 outcome_reports 有非空 score_total → peer_destinations.has_data=True 且
  score_ref=该回传分（真实数据聚合，不 mock build_peer_destinations）
- 从未回传分数（无 outcome_reports 或 score_total 全空）→ has_data=False 诚实降级
"""

from uuid import uuid4

from app.models.assessment import Assessment
from app.models.outcome_report import AdmissionPath, OutcomeReport, OutcomeType
from app.services.assessment_interpret_service import build_interpretation


def _make_report(*, user_id, score_total: int | None) -> OutcomeReport:
    return OutcomeReport(
        user_id=user_id,
        outcome_type=OutcomeType.grad_civil_career,
        actual_school="中山大学" if score_total is not None else None,
        score_total=score_total,
        admission_path=AdmissionPath.normal,
        year=2025,
        is_public="public",
    )


def _make_assessment(user_id) -> Assessment:
    return Assessment(
        user_id=user_id,
        assessment_type="holland",
        answers={"q1": "R"},
        result_code="RIA",
        result_summary="测试结果描述",
        scores={"R": 9, "I": 8, "A": 7, "S": 6, "E": 5, "C": 4},
    )


def test_peer_uses_own_reported_score(db_session):
    uid = uuid4()
    other = uuid4()
    db_session.add_all(
        [
            _make_assessment(uid),
            _make_report(user_id=uid, score_total=345),
            # 同窗 [315, 375] 内另一用户的真实回传
            _make_report(user_id=other, score_total=350),
        ]
    )
    db_session.commit()

    resp = build_interpretation(db_session, uid)
    assert resp["has_assessment"] is True
    peer = resp["peer_destinations"]
    assert peer["has_data"] is True
    assert peer["score_ref"] == 345
    assert peer["peer_count"] >= 2


def test_peer_empty_when_never_reported_score(db_session):
    uid = uuid4()
    db_session.add(_make_assessment(uid))
    # 回传过但 score_total 为空（就业上岸未填分）→ 同样视为无参照分
    db_session.add(_make_report(user_id=uid, score_total=None))
    db_session.commit()

    resp = build_interpretation(db_session, uid)
    assert resp["has_assessment"] is True
    peer = resp["peer_destinations"]
    assert peer["has_data"] is False
    assert peer["distribution"] == []
