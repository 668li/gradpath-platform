# backend/tests/test_assessment_interpret.py
"""interpret 接线测试 — 同分人群去向使用用户自己真实回传分 + 无测评也可出路径。

覆盖：
- 用户在 outcome_reports 有非空 score_total → peer_destinations.has_data=True 且
  score_ref=该回传分（真实数据聚合，不 mock build_peer_destinations）
- 从未回传分数（无 outcome_reports 或 score_total 全空）→ has_data=False 诚实降级
- 倒置（2026-09-05）：无测评但 profile 有专业 → 仍返回完整路径结构
  （has_assessment=False、assessment=None、interpretation 诚实标注无测评信号）
- 无测评且 profile 无专业 → recommendation 诚实引导补档案，不生成空聚合假数据
"""

from uuid import uuid4

from app.models.assessment import Assessment
from app.models.career_profile import CareerProfile
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


def _make_profile(user_id, *, major: str | None) -> CareerProfile:
    return CareerProfile(user_id=user_id, major=major)


def test_no_assessment_but_major_still_returns_paths_structure(db_session):
    """倒置：无测评 + profile 有专业 → 完整路径结构，诚实标注无测评信号。"""
    uid = uuid4()
    db_session.add(_make_profile(uid, major="计算机科学与技术"))
    db_session.commit()

    resp = build_interpretation(db_session, uid)
    assert resp["has_assessment"] is False
    assert resp["assessment"] is None
    assert isinstance(resp["paths"], list)
    assert isinstance(resp["recommendation"], str) and resp["recommendation"]
    assert "测评" in resp["interpretation"]["reason"]
    # 不伪造同分人群/专业前景
    assert resp["peer_destinations"]["has_data"] is False


def test_no_assessment_no_major_honest_guidance(db_session):
    """无测评 + 无专业 → recommendation 诚实引导补档案，绝不编造路径。"""
    uid = uuid4()
    db_session.add(_make_profile(uid, major=None))
    db_session.commit()

    resp = build_interpretation(db_session, uid)
    assert resp["has_assessment"] is False
    assert resp["assessment"] is None
    assert resp["paths"] == []
    assert "个人档案" in resp["recommendation"]
    assert "测评" in resp["interpretation"]["reason"]


def test_profile_enum_education_does_not_crash(db_session):
    """回归（2026-09-05 生产冒烟 KeyError: 'bachelor'）：档案学历存英文枚举值，
    interpret 必须映射成中文档位再喂决策引擎，绝不把枚举直传进 _EDU_RANK。"""
    uid = uuid4()
    db_session.add(
        CareerProfile(
            user_id=uid,
            major="计算机科学与技术",
            education_level="bachelor",
            graduation_year=2026,
        )
    )
    db_session.commit()

    resp = build_interpretation(db_session, uid)  # 旧代码此处 KeyError → 500
    assert resp["has_assessment"] is False
    assert isinstance(resp["paths"], list)
    assert isinstance(resp["recommendation"], str)
