"""国考职位 API 测试 — 列表/筛选/分页/详情/统计。"""
from datetime import datetime, timezone

import pytest

from app.models.gwy_position import GwyPosition


def _utcnow():
    return datetime.now(timezone.utc)


def _make_position(
    id_suffix: str,
    *,
    position_code: str,
    dept_name: str = "测试部门",
    position_name: str = "一级科员",
    major_req: str = "计算机类",
    education_req: str = "本科及以上",
    political_status: str = "不限",
    org_level: str = "县（区）级及以下",
    exam_category: str = "行政执法类",
    work_location: str = "北京市东城区",
    recruit_count: int = 1,
) -> GwyPosition:
    now = _utcnow()
    return GwyPosition(
        id=f"id-{id_suffix}",
        year=2026,
        exam_type="国考",
        dept_code=f"1301{id_suffix}",
        dept_name=dept_name,
        bureau="测试局",
        agency_type="中央国家行政机关省级以下直属机构",
        position_name=position_name,
        position_attr="普通职位",
        position_distribution="其他职位",
        position_desc="测试职位描述",
        position_code=position_code,
        org_level=org_level,
        exam_category=exam_category,
        recruit_count=recruit_count,
        major_req=major_req,
        education_req=education_req,
        degree_req="与最高学历相对应的学位",
        political_status=political_status,
        min_work_years="无限制",
        grassroots_exp_req="无限制",
        professional_test="否",
        interview_ratio="3:1",
        work_location=work_location,
        settle_location=work_location,
        remarks=None,
        dept_website="http://example.gov.cn",
        phone1="010-12345678",
        phone2=None,
        phone3=None,
        sheet_name="中央国家行政机关省级以下直属机构",
        source_url="http://dl.scs.gov.cn/download/8a81f6d19780e4080199e13f881f0153",
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def seed_positions(db_session):
    positions = [
        _make_position(
            "1",
            position_code="130110001001",
            dept_name="国家税务总局北京市税务局",
            position_name="一级行政执法员（一）",
            education_req="本科及以上",
            work_location="北京市东城区",
            recruit_count=3,
        ),
        _make_position(
            "2",
            position_code="130110001002",
            dept_name="国家税务总局北京市税务局",
            position_name="一级行政执法员（二）",
            education_req="仅限本科",
            work_location="北京市西城区",
        ),
        _make_position(
            "3",
            position_code="130110002001",
            dept_name="国家税务总局上海市税务局",
            position_name="一级行政执法员（一）",
            education_req="硕士研究生及以上",
            work_location="上海市黄浦区",
            political_status="中共党员",
            org_level="市（地）级",
            exam_category="综合管理类",
        ),
        _make_position(
            "4",
            position_code="130110003001",
            dept_name="财政部办公厅",
            position_name="政策研究岗",
            major_req="经济学类",
            education_req="仅限博士研究生",
            work_location="北京市西城区",
            org_level="中央",
        ),
    ]
    db_session.add_all(positions)
    db_session.commit()
    return positions


def test_list_positions_default(client, seed_positions):
    resp = client.get("/api/gwy-positions")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 4
    assert data["page"] == 1
    assert data["page_size"] == 20
    assert len(data["items"]) == 4
    # 字段完整透出
    first = data["items"][0]
    assert first["id"] == "id-1"
    assert first["position_code"] == "130110001001"
    assert first["recruit_count"] == 3
    assert first["dept_name"] == "国家税务总局北京市税务局"


def test_list_positions_pagination(client, seed_positions):
    resp = client.get("/api/gwy-positions", params={"page": 1, "page_size": 2})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 4
    assert len(data["items"]) == 2
    assert data["page_size"] == 2

    resp2 = client.get("/api/gwy-positions", params={"page": 3, "page_size": 2})
    data2 = resp2.json()
    assert data2["total"] == 4
    assert len(data2["items"]) == 0


def test_list_positions_keyword_filter(client, seed_positions):
    resp = client.get("/api/gwy-positions", params={"q": "政策研究"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["position_name"] == "政策研究岗"

    # 通配符作为字面量转义，不应全量命中
    resp2 = client.get("/api/gwy-positions", params={"q": "%"})
    assert resp2.status_code == 200
    assert resp2.json()["total"] == 0


def test_list_positions_education_filter(client, seed_positions):
    resp = client.get("/api/gwy-positions", params={"education_req": "仅限本科"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["education_req"] == "仅限本科"


def test_list_positions_province_filter(client, seed_positions):
    resp = client.get("/api/gwy-positions", params={"province": "北京"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    assert all(i["work_location"].startswith("北京") for i in data["items"])


def test_list_positions_position_code_filter(client, seed_positions):
    resp = client.get(
        "/api/gwy-positions", params={"position_code": "130110002001"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["dept_name"] == "国家税务总局上海市税务局"


def test_list_positions_political_status_filter(client, seed_positions):
    resp = client.get("/api/gwy-positions", params={"political_status": "中共党员"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["political_status"] == "中共党员"


def test_get_position_detail(client, seed_positions):
    resp = client.get("/api/gwy-positions/id-1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "id-1"
    assert data["year"] == 2026
    assert data["exam_type"] == "国考"
    assert data["position_name"] == "一级行政执法员（一）"


def test_get_position_detail_not_found(client, seed_positions):
    resp = client.get("/api/gwy-positions/id-not-exists")
    assert resp.status_code == 404


def test_stats(client, seed_positions):
    resp = client.get("/api/gwy-positions/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 4

    edu = {g["key"]: g["count"] for g in data["by_education"]}
    assert edu == {"本科及以上": 1, "仅限本科": 1, "硕士研究生及以上": 1, "仅限博士研究生": 1}

    # 省份按 work_location 前缀分组（北京市、上海市）
    provinces = {g["key"] for g in data["by_province"]}
    assert provinces == {"北京市东城区", "北京市西城区", "上海市黄浦区"}

    org = {g["key"]: g["count"] for g in data["by_org_level"]}
    assert org.get("县（区）级及以下") == 2


def test_stats_year_filter(client, seed_positions):
    resp = client.get("/api/gwy-positions/stats", params={"year": 2025})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["by_education"] == []


def test_public_endpoint_no_auth_required(client, seed_positions):
    """公开只读端点：无 token 直接可访问。"""
    assert client.get("/api/gwy-positions").status_code == 200
    assert client.get("/api/gwy-positions/id-1").status_code == 200
    assert client.get("/api/gwy-positions/stats").status_code == 200
