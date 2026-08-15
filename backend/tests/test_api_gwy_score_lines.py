"""国考进面分数线 API 测试 — 列表/筛选/分页/统计。"""
from datetime import datetime, timezone

import pytest

from app.models.gwy_score_line import GwyScoreLine


def _utcnow():
    return datetime.now(timezone.utc)


def _make_score_line(
    id_suffix: str,
    *,
    position_code: str,
    batch: str = "首批",
    dept_name: str = "国家税务总局北京市税务局",
    position_name: str = "一级行政执法员（一）",
    min_score: float = 128.5,
) -> GwyScoreLine:
    now = _utcnow()
    return GwyScoreLine(
        id=f"sl-{id_suffix}",
        year=2026,
        batch=batch,
        dept_name=dept_name,
        dept_code="130101",
        bureau="测试局",
        position_name=position_name,
        position_code=position_code,
        min_score=min_score,
        source_url="http://dl.scs.gov.cn/download/8a81f6d09bb1deaf019bbfaf036b0011",
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def seed_score_lines(db_session):
    lines = [
        _make_score_line(
            "1",
            position_code="130110001001",
            dept_name="国家税务总局北京市税务局",
            min_score=128.5,
        ),
        _make_score_line(
            "2",
            position_code="130110001002",
            dept_name="国家税务总局北京市税务局",
            position_name="一级行政执法员（二）",
            min_score=131.2,
        ),
        _make_score_line(
            "3",
            position_code="130110002001",
            dept_name="国家税务总局上海市税务局",
            min_score=125.0,
            batch="调剂",
        ),
        _make_score_line(
            "4",
            position_code="130110003001",
            dept_name="财政部办公厅",
            position_name="政策研究岗",
            min_score=140.5,
            batch="补充录用",
        ),
    ]
    db_session.add_all(lines)
    db_session.commit()
    return lines


def test_list_score_lines_default(client, seed_score_lines):
    resp = client.get("/api/gwy-score-lines")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 4
    assert data["page"] == 1
    assert data["page_size"] == 20
    assert len(data["items"]) == 4
    first = data["items"][0]
    assert first["id"] == "sl-4"  # 默认按最低面试分数降序，140.5 最高
    assert first["position_code"] == "130110003001"
    assert first["min_score"] == 140.5
    assert first["batch"] == "补充录用"


def test_list_score_lines_pagination(client, seed_score_lines):
    resp = client.get("/api/gwy-score-lines", params={"page": 1, "page_size": 2})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 4
    assert len(data["items"]) == 2

    resp2 = client.get("/api/gwy-score-lines", params={"page": 3, "page_size": 2})
    data2 = resp2.json()
    assert data2["total"] == 4
    assert len(data2["items"]) == 0


def test_list_score_lines_position_code_filter(client, seed_score_lines):
    resp = client.get(
        "/api/gwy-score-lines", params={"position_code": "130110001001"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["dept_name"] == "国家税务总局北京市税务局"


def test_list_score_lines_batch_filter(client, seed_score_lines):
    resp = client.get("/api/gwy-score-lines", params={"batch": "调剂"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["min_score"] == 125.0


def test_list_score_lines_keyword_filter(client, seed_score_lines):
    resp = client.get("/api/gwy-score-lines", params={"q": "政策研究"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["position_name"] == "政策研究岗"

    # 通配符作为字面量转义，不应全量命中
    resp2 = client.get("/api/gwy-score-lines", params={"q": "%"})
    assert resp2.status_code == 200
    assert resp2.json()["total"] == 0


def test_list_score_lines_sorted_by_score_desc(client, seed_score_lines):
    resp = client.get("/api/gwy-score-lines")
    data = resp.json()
    scores = [i["min_score"] for i in data["items"]]
    assert scores == sorted(scores, reverse=True)


def test_stats(client, seed_score_lines):
    resp = client.get("/api/gwy-score-lines/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 4
    assert data["avg_score"] == 131.3  # (128.5 + 131.2 + 125 + 140.5) / 4 = 131.3

    by_batch = {g["key"]: g["count"] for g in data["by_batch"]}
    assert by_batch == {"首批": 2, "调剂": 1, "补充录用": 1}

    by_year = {g["key"]: g["count"] for g in data["by_year"]}
    assert by_year == {"2026": 4}


def test_stats_year_filter(client, seed_score_lines):
    resp = client.get("/api/gwy-score-lines/stats", params={"year": 2025})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["avg_score"] is None
    assert data["by_batch"] == []


def test_public_endpoint_no_auth_required(client, seed_score_lines):
    """公开只读端点：无 token 直接可访问。"""
    assert client.get("/api/gwy-score-lines").status_code == 200
    assert client.get("/api/gwy-score-lines/stats").status_code == 200
