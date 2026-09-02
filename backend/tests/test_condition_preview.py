"""免费可报性预览端点测试 — 免登录「先尝一口」漏斗入口。

用 SQLite in-memory（conftest 的 client fixture），避开本地 PG 依赖。
覆盖：
- 国考：可报 / 应届 / 政治面貌 / 性别 / 学历 各维度被挡
- 省考：可报 / 应届被挡
- 考研：估分 vs 复试线三档（稳健/均衡/冲刺）+ 无分数线降级
- 404 / 校验
"""

from datetime import datetime, timezone

from app.models.grad_intel import GradScorelineRecord, GradYanzhaoProgram
from app.models.gwy_position import GwyPosition
from app.models.gwy_province_position import GwyProvincePosition


def _utcnow():
    return datetime.now(timezone.utc)


def _make_gwy_position(
    id_suffix: str,
    *,
    position_code: str,
    political_status: str = "不限",
    education_req: str = "本科及以上",
    remarks: str | None = None,
    grassroots_exp_req: str = "无限制",
):
    now = _utcnow()
    return GwyPosition(
        id=f"gwy-{id_suffix}",
        year=2026,
        exam_type="国考",
        dept_code=f"1301{id_suffix}",
        dept_name="国家税务总局某市税务局",
        bureau="国家税务总局",
        agency_type="省级以下直属机构",
        position_name="一级行政执法员",
        position_attr="普通职位",
        position_distribution="其他职位",
        position_desc="测试",
        position_code=position_code,
        org_level="县（区）级及以下",
        exam_category="行政执法类",
        recruit_count=1,
        major_req="不限",
        education_req=education_req,
        degree_req="与最高学历相对应的学位",
        political_status=political_status,
        min_work_years="无限制",
        grassroots_exp_req=grassroots_exp_req,
        professional_test="否",
        interview_ratio="3:1",
        work_location="广东省广州市",
        settle_location="广东省广州市",
        remarks=remarks,
        dept_website="http://example.gov.cn",
        phone1="010-12345678",
        sheet_name="省级以下直属机构",
        source_url="http://dl.scs.gov.cn/mock/positions.xlsx",
        created_at=now,
        updated_at=now,
    )


def _make_province_position(
    id_suffix: str,
    *,
    position_code: str,
    education_req: str = "本科",
    fresh_grad_only: str = "否",
    grassroots_exp_req: str = "否",
):
    now = _utcnow()
    return GwyProvincePosition(
        id=f"prov-{id_suffix}",
        year=2026,
        province="广东",
        dept_code=f"1000{id_suffix}",
        dept_name="广东省XX厅",
        position_code=position_code,
        position_name="一级科员",
        education_req=education_req,
        degree_req="学士",
        fresh_grad_only=fresh_grad_only,
        grassroots_exp_req=grassroots_exp_req,
        other_requirements="",
        exam_region="省直",
        sheet_name="广东省直机关",
        source_url="http://gd.gov.cn/mock/positions.xlsx",
        created_at=now,
        updated_at=now,
    )


def _make_yz(university: str, major: str, quota: int, year: int = 2026):
    return GradYanzhaoProgram(
        university_name=university,
        department="计算机学院",
        major_name=major,
        degree_type="学硕",
        enrollment_quota=quota,
        source_url="http://yz.chsi.com.cn/mock",
        year=year,
        data_sources=["研招网硕士目录"],
    )


def _make_scoreline(
    university: str,
    major: str,
    year: int,
    score: int,
    politics: int | None = None,
):
    return GradScorelineRecord(
        university_name=university,
        major_name=major,
        year=year,
        total_score_line=score,
        politics_score=politics,
        data_sources=["scorelines_real_data.json:2026-07-12"],
    )


def test_national_eligible(client, db_session):
    db_session.add(_make_gwy_position("01", position_code="13010101001"))
    db_session.commit()

    resp = client.post(
        "/api/condition-checklist/preview",
        json={
            "exam_source": "national",
            "position_ref": "gwy-01",
            "fresh_status": "应届",
            "party_status": "群众",
            "education": "本科",
            "gender": "男",
            "has_grassroots": False,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["eligible"] is True
    assert data["blockers"] == []
    assert data["position_name"] == "一级行政执法员"
    assert "可以报考" in data["verdict_text"]


def test_national_blocked_by_fresh(client, db_session):
    db_session.add(_make_gwy_position("02", position_code="13010101002", remarks="仅限应届毕业生"))
    db_session.commit()

    resp = client.post(
        "/api/condition-checklist/preview",
        json={
            "exam_source": "national",
            "position_ref": "gwy-02",
            "fresh_status": "非应届",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["eligible"] is False
    assert [b["key"] for b in data["blockers"]] == ["fresh_grad"]


def test_national_blocked_by_party(client, db_session):
    db_session.add(
        _make_gwy_position("03", position_code="13010101003", political_status="中共党员")
    )
    db_session.commit()

    resp = client.post(
        "/api/condition-checklist/preview",
        json={
            "exam_source": "national",
            "position_ref": "gwy-03",
            "party_status": "群众",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["eligible"] is False
    assert [b["key"] for b in data["blockers"]] == ["party_status"]


def test_national_blocked_by_gender(client, db_session):
    db_session.add(_make_gwy_position("04", position_code="13010101004", remarks="限女性"))
    db_session.commit()

    resp = client.post(
        "/api/condition-checklist/preview",
        json={
            "exam_source": "national",
            "position_ref": "gwy-04",
            "gender": "男",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["eligible"] is False
    assert [b["key"] for b in data["blockers"]] == ["gender"]


def test_national_blocked_by_education(client, db_session):
    db_session.add(_make_gwy_position("05", position_code="13010101005", education_req="仅限硕士"))
    db_session.commit()

    resp = client.post(
        "/api/condition-checklist/preview",
        json={
            "exam_source": "national",
            "position_ref": "gwy-05",
            "education": "本科",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["eligible"] is False
    assert [b["key"] for b in data["blockers"]] == ["education"]


def test_province_eligible_and_blocked(client, db_session):
    db_session.add(_make_province_position("01", position_code="10010101", fresh_grad_only="否"))
    db_session.add(_make_province_position("02", position_code="10010102", fresh_grad_only="是"))
    db_session.commit()

    resp_ok = client.post(
        "/api/condition-checklist/preview",
        json={
            "exam_source": "province",
            "position_ref": "prov-01",
            "fresh_status": "非应届",
            "education": "本科",
        },
    )
    assert resp_ok.status_code == 200
    assert resp_ok.json()["eligible"] is True

    resp_blocked = client.post(
        "/api/condition-checklist/preview",
        json={
            "exam_source": "province",
            "position_ref": "prov-02",
            "fresh_status": "非应届",
        },
    )
    assert resp_blocked.status_code == 200
    data = resp_blocked.json()
    assert data["eligible"] is False
    assert [b["key"] for b in data["blockers"]] == ["fresh_grad"]


def test_kaoyan_levels(client, db_session):
    yz = _make_yz("清华大学", "计算机科学与技术", 10)
    db_session.add(yz)
    db_session.add(_make_scoreline("清华大学", "计算机科学与技术", 2025, 310, politics=50))
    db_session.commit()
    ref = str(yz.id)

    # 稳健：估分高于复试线 10+（_STEADY_DIFF=10）
    resp = client.post(
        "/api/condition-checklist/preview",
        json={
            "exam_source": "kaoyan",
            "position_ref": ref,
            "kaoyan_estimated_score": 340,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["level"] == "稳健"
    assert data["total_score_line"] == 310
    assert data["score_lines"]["politics"] == 50
    assert data["eligible"] is None

    # 冲刺：估分低于复试线 10+
    resp = client.post(
        "/api/condition-checklist/preview",
        json={
            "exam_source": "kaoyan",
            "position_ref": ref,
            "kaoyan_estimated_score": 295,
        },
    )
    assert resp.json()["level"] == "冲刺"

    # 均衡：|diff| < 10
    resp = client.post(
        "/api/condition-checklist/preview",
        json={
            "exam_source": "kaoyan",
            "position_ref": ref,
            "kaoyan_estimated_score": 305,
        },
    )
    assert resp.json()["level"] == "均衡"


def test_kaoyan_no_scoreline_degrades_gracefully(client, db_session):
    yz = _make_yz("某大学", "某专业", 5)
    db_session.add(yz)
    db_session.commit()

    resp = client.post(
        "/api/condition-checklist/preview",
        json={
            "exam_source": "kaoyan",
            "position_ref": str(yz.id),
            "kaoyan_estimated_score": 300,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["level"] is None
    assert data["total_score_line"] is None
    assert "暂无有效复试线" in data["verdict_text"]


def test_position_not_found(client, db_session):
    resp = client.post(
        "/api/condition-checklist/preview",
        json={"exam_source": "national", "position_ref": "gwy-does-not-exist"},
    )
    assert resp.status_code == 404


def test_invalid_exam_source(client, db_session):
    resp = client.post(
        "/api/condition-checklist/preview",
        json={"exam_source": "unknown", "position_ref": "gwy-01"},
    )
    assert resp.status_code == 422
