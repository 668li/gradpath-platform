# backend/tests/test_peer_destinations.py
"""同分人群去向聚合测试 — build_peer_destinations。

覆盖：
- 无参照分 → has_data=false
- 空库 → has_data=false，不抛错
- seed outcome_reports 后按 ±30 分窗聚合正确（count / rate / label 派生）
- 窗外的样本不计入
"""

from uuid import uuid4

from sqlalchemy import inspect

from app.models.outcome_report import AdmissionPath, OutcomeReport, OutcomeType
from app.services.path_comparison_service import build_peer_destinations


def _make_report(
    *,
    user_id,
    score_total: int,
    outcome_type: OutcomeType = OutcomeType.grad_civil_career,
    actual_school: str | None = None,
    year: int = 2025,
) -> OutcomeReport:
    return OutcomeReport(
        user_id=user_id,
        outcome_type=outcome_type,
        actual_school=actual_school,
        score_total=score_total,
        admission_path=AdmissionPath.normal,
        year=year,
        is_public="public",
    )


def test_no_score_returns_empty(db_session):
    result = build_peer_destinations(db_session, None)
    assert result["has_data"] is False
    assert result["peer_count"] == 0
    assert result["distribution"] == []


def test_empty_db_returns_empty(db_session):
    result = build_peer_destinations(db_session, 345)
    assert result["has_data"] is False
    assert result["peer_count"] == 0
    assert result["distribution"] == []


def test_aggregates_within_score_window(db_session):
    uid = uuid4()
    db_session.add_all(
        [
            # 窗 [315, 375] 内：2 条上岸中山 + 1 条未上岸
            _make_report(user_id=uid, score_total=340, actual_school="中山大学"),
            _make_report(user_id=uid, score_total=350, actual_school="中山大学"),
            _make_report(user_id=uid, score_total=360, outcome_type=OutcomeType.failed),
            # 窗外（500）：不计入
            _make_report(user_id=uid, score_total=500, actual_school="北京大学"),
        ]
    )
    db_session.commit()

    result = build_peer_destinations(db_session, 345)
    assert result["has_data"] is True
    assert result["score_ref"] == 345
    assert result["peer_count"] == 3

    labels = [(d["label"], d["count"]) for d in result["distribution"]]
    assert ("上岸 中山大学", 2) in labels
    assert ("未上岸", 1) in labels

    # 占比 = 该去向样本 / 同分总样本（service 端 round 到 3 位）
    by_label = {d["label"]: d for d in result["distribution"]}
    assert by_label["上岸 中山大学"]["rate"] == round(2 / 3, 3)
    assert by_label["未上岸"]["rate"] == round(1 / 3, 3)


def test_adjustment_label_prefix(db_session):
    """调剂去向 label 以『调剂』开头。"""
    uid = uuid4()
    db_session.add_all(
        [
            _make_report(
                user_id=uid,
                score_total=360,
                outcome_type=OutcomeType.adjustment,
                actual_school="华南理工大学",
            ),
        ]
    )
    db_session.commit()

    result = build_peer_destinations(db_session, 360)
    assert result["has_data"] is True
    assert result["distribution"][0]["label"] == "调剂 华南理工大学"
    assert result["distribution"][0]["count"] == 1


def test_outcome_reports_table_has_expected_columns(db_session):
    """回归护栏：聚合依赖的列存在（score_total / outcome_type / actual_school）。"""
    cols = {c.name for c in inspect(OutcomeReport).columns}
    assert {"score_total", "outcome_type", "actual_school"} <= cols
