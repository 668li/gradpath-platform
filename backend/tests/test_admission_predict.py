# backend/tests/test_admission_predict.py
"""录取预测端点测试 — 聚焦 P0-2「缺分数不编数」信任修复。

覆盖：
- 有可溯源记录但全无复试分 → 低置信 + data_note 显式标注数据不足，不再 [350] 兜底
- 有真实复试分 → 正常预测路径，无 data_note
- 完全无记录 → 低置信早退（既有行为）
"""

from app.models.grad_intel import GradScorelineRecord


def _make_scoreline(
    university: str,
    major: str,
    year: int,
    score: int | None,
):
    return GradScorelineRecord(
        university_name=university,
        major_name=major,
        year=year,
        total_score_line=score,
        data_sources=["scorelines_real_data.json:2026-07-12"],
    )


def _payload(**overrides):
    base = {
        "school_name": "某高校",
        "major": "某专业",
        "user_score": 400,
        "user_gpa": 3.5,
        "user_university": "某大学",
    }
    base.update(overrides)
    return base


def test_predict_no_score_data_returns_low_confidence(client, auth_headers, db_session):
    """有可溯源记录但 total_score_line 全空 → 低置信 + data_note，禁止 [350] 编造。"""
    db_session.add(_make_scoreline("某高校", "某专业", 2025, None))
    db_session.commit()

    resp = client.post(
        "/api/admission/predict",
        headers=auth_headers,
        json=_payload(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["confidence"] == "low"
    assert data["probability"] < 0.5
    assert data["risk_level"] == "high"
    assert data["similar_cases"] == []
    assert data["data_note"] and "真实复试分数线" in data["data_note"]
    assert "无法可靠预测" in data["recommendation"]


def test_predict_with_real_score_normal_path(client, auth_headers, db_session):
    """有真实复试分 → 正常预测路径，无数据不足标注。"""
    db_session.add(_make_scoreline("某高校", "某专业", 2025, 310))
    db_session.commit()

    resp = client.post(
        "/api/admission/predict",
        headers=auth_headers,
        json=_payload(user_score=340),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["confidence"] in ("high", "medium", "low")
    assert data.get("data_note") in (None, "")
    assert "历史均分" in data["factors"][0]["factor"]


def test_predict_no_records_returns_low_confidence(client, auth_headers, db_session):
    """完全无记录 → 低置信早退（既有行为保持）。"""
    resp = client.post(
        "/api/admission/predict",
        headers=auth_headers,
        json=_payload(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["confidence"] == "low"
    assert data["data_note"] in (None, "")
    assert "暂无历史数据" in data["recommendation"]
