"""省考职位 API 测试 — 列表/筛选/分页/详情/统计（数据源：广东省 2026 省考职位表）。"""

from datetime import datetime, timezone

import pytest

from app.models.gwy_province_position import GwyProvincePosition


def _utcnow():
    return datetime.now(timezone.utc)


def _make_position(
    id_suffix: str,
    *,
    position_code: str,
    dept_name: str = "广东省财政厅",
    position_name: str = "一级主任科员以下",
    education_req: str = "本科",
    exam_region: str = "广州",
    sheet_name: str = "县以上机关",
    position_type: str = "综合管理类",
    recruit_count: int = 1,
    grassroots_exp_req: str = "否",
    psych_test: str | None = None,
    fresh_grad_only: str = "否",
    other_requirements: str = "具有两年以上基层工作经历",
    major_req_grad: str = "财政学(A0202)",
    major_req_undergrad: str = "财政学类(B0202)",
    major_req_junior: str | None = None,
) -> GwyProvincePosition:
    now = _utcnow()
    return GwyProvincePosition(
        id=f"id-{id_suffix}",
        year=2026,
        province="广东",
        dept_code=f"1990007{id_suffix}",
        dept_name=dept_name,
        position_name=position_name,
        position_code=position_code,
        position_desc="负责机关综合事务管理",
        position_type=position_type,
        recruit_count=recruit_count,
        education_req=education_req,
        degree_req="学士",
        major_req_grad=major_req_grad,
        major_req_undergrad=major_req_undergrad,
        major_req_junior=major_req_junior,
        grassroots_exp_req=grassroots_exp_req,
        psych_test=psych_test,
        fresh_grad_only=fresh_grad_only,
        other_requirements=other_requirements,
        exam_region=exam_region,
        sheet_name=sheet_name,
        source_url="https://www.gdzz.gov.cn/public/广东省2026年考试录用公务员公告附件.zip",
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def seed_positions(db_session):
    positions = [
        _make_position(
            "1",
            position_code="19900072641001",
            dept_name="中共广东省委老干部局",
            position_name="综合岗一级主任科员以下",
            education_req="研究生",
            exam_region="广州",
            recruit_count=2,
        ),
        _make_position(
            "2",
            position_code="19900072641002",
            dept_name="广东省公安厅",
            position_name="执法勤务岗",
            education_req="本科",
            exam_region="广州",
            sheet_name="公安",
            position_type="执法勤务类",
            psych_test="是",
            fresh_grad_only="是",
            major_req_grad="公安学(A0306)",
            major_req_undergrad="公安学类(B0306)",
        ),
        _make_position(
            "3",
            position_code="12300010101001",
            dept_name="广州市中级人民法院",
            position_name="法官助理",
            education_req="本科",
            exam_region="深圳",
            sheet_name="法院",
            position_type="审判辅助类",
            major_req_grad="法学(A0301)",
            major_req_undergrad="法学类(B0301)",
        ),
        _make_position(
            "4",
            position_code="62300010101001",
            dept_name="梅州市五华县乡镇人民政府",
            position_name="乡镇机关科员",
            education_req="大专",
            exam_region="梅州",
            sheet_name="乡镇机关",
            position_type="综合管理类",
            grassroots_exp_req="是",
            major_req_grad=None,
            major_req_undergrad="不限",
            major_req_junior=None,
        ),
    ]
    db_session.add_all(positions)
    db_session.commit()
    return positions


def test_list_positions_default(client, seed_positions):
    resp = client.get("/api/gwy-province-positions")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 4
    assert data["page"] == 1
    assert data["page_size"] == 20
    assert len(data["items"]) == 4
    # 字段完整透出
    first = data["items"][0]
    assert first["id"] == "id-1"
    assert first["position_code"] == "19900072641001"
    assert first["province"] == "广东"
    assert first["year"] == 2026
    assert first["dept_name"] == "中共广东省委老干部局"
    assert first["recruit_count"] == 2
    assert first["exam_region"] == "广州"


def test_list_positions_pagination(client, seed_positions):
    resp = client.get("/api/gwy-province-positions", params={"page": 1, "page_size": 2})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 4
    assert len(data["items"]) == 2
    assert data["page_size"] == 2

    resp2 = client.get("/api/gwy-province-positions", params={"page": 3, "page_size": 2})
    data2 = resp2.json()
    assert data2["total"] == 4
    assert len(data2["items"]) == 0


def test_list_positions_keyword_filter(client, seed_positions):
    resp = client.get("/api/gwy-province-positions", params={"q": "法官助理"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["position_name"] == "法官助理"

    # 专业要求字段（研究生专业列）应参与模糊匹配
    resp2 = client.get("/api/gwy-province-positions", params={"q": "财政学"})
    assert resp2.status_code == 200
    assert resp2.json()["total"] == 1

    # 通配符作为字面量转义，不应全量命中
    resp3 = client.get("/api/gwy-province-positions", params={"q": "%"})
    assert resp3.status_code == 200
    assert resp3.json()["total"] == 0


def test_list_positions_education_filter(client, seed_positions):
    resp = client.get("/api/gwy-province-positions", params={"education_req": "研究生"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["education_req"] == "研究生"


def test_list_positions_region_filter(client, seed_positions):
    resp = client.get("/api/gwy-province-positions", params={"exam_region": "广州"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert all(i["exam_region"] == "广州" for i in data["items"])


def test_list_positions_sheet_filter(client, seed_positions):
    resp = client.get("/api/gwy-province-positions", params={"sheet_name": "公安"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["dept_name"] == "广东省公安厅"


def test_list_positions_fresh_grad_filter(client, seed_positions):
    resp = client.get("/api/gwy-province-positions", params={"fresh_grad_only": "是"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["fresh_grad_only"] == "是"


def test_list_positions_position_code_filter(client, seed_positions):
    resp = client.get("/api/gwy-province-positions", params={"position_code": "19900072641001"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["dept_name"] == "中共广东省委老干部局"


def test_list_positions_province_and_year_filter(client, seed_positions):
    resp = client.get(
        "/api/gwy-province-positions",
        params={"province": "广东", "year": 2025},
    )
    assert resp.status_code == 200
    assert resp.json()["total"] == 0

    resp2 = client.get("/api/gwy-province-positions", params={"province": "广东"})
    assert resp2.status_code == 200
    assert resp2.json()["total"] == 4


def test_get_position_detail(client, seed_positions):
    resp = client.get("/api/gwy-province-positions/id-1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "id-1"
    assert data["year"] == 2026
    assert data["province"] == "广东"
    assert data["position_name"] == "综合岗一级主任科员以下"
    assert data["position_type"] == "综合管理类"
    assert data["major_req_undergrad"] == "财政学类(B0202)"


def test_get_position_detail_not_found(client, seed_positions):
    resp = client.get("/api/gwy-province-positions/id-not-exists")
    assert resp.status_code == 404


def test_stats(client, seed_positions):
    resp = client.get("/api/gwy-province-positions/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 4
    # 总招录人数 = SUM(recruit_count) = 2+1+1+1
    assert data["total_recruit"] == 5

    edu = {g["key"]: g["count"] for g in data["by_education"]}
    assert edu == {"研究生": 1, "本科": 2, "大专": 1}

    sheet = {g["key"]: g["count"] for g in data["by_sheet"]}
    assert sheet == {"县以上机关": 1, "公安": 1, "法院": 1, "乡镇机关": 1}

    region = {g["key"]: g["count"] for g in data["by_region"]}
    assert region == {"广州": 2, "深圳": 1, "梅州": 1}

    fresh = {g["key"]: g["count"] for g in data["by_fresh_grad_only"]}
    assert fresh == {"否": 3, "是": 1}


def test_stats_province_and_year_filter(client, seed_positions):
    resp = client.get(
        "/api/gwy-province-positions/stats", params={"province": "广东", "year": 2025}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["total_recruit"] == 0
    assert data["by_education"] == []


def test_public_endpoint_no_auth_required(client, seed_positions):
    """公开只读端点：无 token 直接可访问。"""
    assert client.get("/api/gwy-province-positions").status_code == 200
    assert client.get("/api/gwy-province-positions/id-1").status_code == 200
    assert client.get("/api/gwy-province-positions/stats").status_code == 200
