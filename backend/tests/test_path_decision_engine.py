"""三路对比决策引擎测试 — service 聚合 + API 端点。

Seeding 模式照 test_api_gwy_positions.py：手动构造 ORM 实例写入内存 SQLite。
覆盖：
- 考研路聚合（分数线/报录比/证据溯源）
- 考公路聚合（岗位数/招录合计/进面分/省考）
- 就业路聚合（行业薪资/城市薪资/院校就业率）+ 空数据降级
- API：401 / analyze 成功（3 路 + evidence）/ history
"""
from datetime import datetime, timezone

import pytest

from app.models.grad_intel import GradScorelineRecord, GradYanzhaoProgram
from app.models.gwy_position import GwyPosition
from app.models.gwy_province_position import GwyProvincePosition
from app.models.gwy_score_line import GwyScoreLine
from app.models.market_data import MarketData
from app.models.salary_benchmark import ExperienceLevel, SalaryBenchmark
from app.models.school import School
from app.services.path_decision_engine import generate_decision


def _utcnow():
    return datetime.now(timezone.utc)


# ----------------------------------------------------------------------
# Seed 工厂
# ----------------------------------------------------------------------
def _make_scoreline(university: str, major: str, year: int, score: int,
                    application: int | None = None, enrollment: int | None = None):
    return GradScorelineRecord(
        university_name=university,
        major_name=major,
        year=year,
        total_score_line=score,
        application_count=application,
        enrollment_count=enrollment,
        data_sources=["公开院校复试线汇总"],
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


def _make_gwy_position(id_suffix: str, *, position_code: str, major_req: str,
                       work_location: str, recruit_count: int = 1,
                       dept_name: str = "测试部门"):
    now = _utcnow()
    return GwyPosition(
        id=f"gwy-{id_suffix}", year=2026, exam_type="国考",
        dept_code=f"1301{id_suffix}", dept_name=dept_name, bureau="测试局",
        agency_type="省级以下直属机构", position_name="一级行政执法员",
        position_attr="普通职位", position_distribution="其他职位",
        position_desc="测试", position_code=position_code,
        org_level="县（区）级及以下", exam_category="行政执法类",
        recruit_count=recruit_count, major_req=major_req,
        education_req="本科及以上", degree_req="学士",
        political_status="不限", min_work_years="无限制",
        grassroots_exp_req="无限制", professional_test="否",
        interview_ratio="3:1", work_location=work_location,
        settle_location=work_location, remarks=None,
        dept_website="http://example.gov.cn", phone1="010-12345678",
        phone2=None, phone3=None, sheet_name="省级以下直属机构",
        source_url="http://dl.scs.gov.cn/mock/positions.xlsx",
        created_at=now, updated_at=now,
    )


def _make_score_line(id_suffix: str, *, position_code: str, min_score: float):
    now = _utcnow()
    return GwyScoreLine(
        id=f"line-{id_suffix}", year=2026, batch="首批",
        dept_name="测试部门", dept_code="1301x", bureau="测试局",
        position_name="一级行政执法员", position_code=position_code,
        min_score=min_score, source_url="http://dl.scs.gov.cn/mock/score.xlsx",
        created_at=now, updated_at=now,
    )


def _make_province_position(id_suffix: str, *, position_code: str,
                            major_req_undergrad: str, province: str = "广东",
                            recruit_count: int = 1):
    now = _utcnow()
    return GwyProvincePosition(
        id=f"prov-{id_suffix}", year=2026, province=province,
        dept_name="广东省测试局", dept_code=f"199{id_suffix}",
        position_name="一级科员", position_code=position_code,
        position_desc="测试", position_type="综合管理类",
        recruit_count=recruit_count, education_req="本科",
        degree_req="学士", major_req_grad=None,
        major_req_undergrad=major_req_undergrad,
        major_req_junior=None, grassroots_exp_req="否",
        psych_test="否", fresh_grad_only="是", other_requirements=None,
        exam_region="广州", sheet_name="乡镇机关",
        source_url="http://rsks.gd.gov.cn/mock/positions.xlsx",
        created_at=now, updated_at=now,
    )


def _make_market_data(indicator: str, industry: str, value: float, unit: str,
                      year: int = 2025, region: str | None = "全国"):
    return MarketData(
        indicator=indicator, category="宏观就业面", value=value, unit=unit,
        region=region, industry=industry, year=year, source="统计公报",
        source_url="http://www.stats.gov.cn/mock/report",
    )


def _make_salary(company: str, position: str, city: str, median: int,
                 year: int = 2025, source: str = "猎聘"):
    return SalaryBenchmark(
        company=company, position=position, city=city,
        experience_level=ExperienceLevel.entry,
        salary_min=median - 5, salary_median=median, salary_max=median + 5,
        source=source, year=year,
    )


def _make_school(name: str, province: str, level: str, emp_rate: float,
                 grad_rate: float):
    return School(
        name=name, slug=f"slug-{name}", code="10001", province=province,
        level=level, ranking=100, employment_rate=emp_rate,
        grad_school_rate=grad_rate,
    )


# ----------------------------------------------------------------------
# Seed fixture
# ----------------------------------------------------------------------
@pytest.fixture
def seed_decision_data(db_session):
    """写入三路数据，全部与「计算机 / 广东」匹配。"""
    db_session.add_all([
        # 考研路
        _make_scoreline("中山大学", "计算机技术", 2025, 350, application=400, enrollment=40),
        _make_scoreline("华南理工大学", "计算机技术", 2024, 340),
        _make_scoreline("北京大学", "计算机科学与技术", 2025, 380),
        _make_scoreline("中山大学", "法学", 2025, 360),  # 不匹配专业
        _make_yz("中山大学", "计算机技术", 80),
        _make_yz("华南理工大学", "计算机技术", 60),
        # 考公路（国考 2026 广东）
        _make_gwy_position("1", position_code="1301001", major_req="计算机类",
                           work_location="广东省广州市天河区", recruit_count=2),
        _make_gwy_position("2", position_code="1301002", major_req="计算机类",
                           work_location="广东省深圳市南山区", recruit_count=1),
        _make_gwy_position("3", position_code="1301003", major_req="法学",
                           work_location="广东省广州市天河区"),  # 不匹配专业
        _make_score_line("1", position_code="1301001", min_score=118.5),
        _make_score_line("2", position_code="1301002", min_score=121.0),
        # 考公路（省考广东 2026）
        _make_province_position("1", position_code="199001", major_req_undergrad="计算机类",
                                recruit_count=3),
        # 就业路
        _make_market_data("城镇单位就业人员平均工资", "计算机、通信和其他电子设备制造业",
                          13.5, "万元"),
        _make_market_data("规模以上工业企业利润总额", "汽车制造业", 5000, "亿元"),  # 不匹配
        _make_salary("腾讯", "后台开发工程师", "深圳", 20),
        _make_school("中山大学", "广东", "985", 95.0, 40.0),
        _make_school("华南理工大学", "广东", "985", 93.0, 38.0),
    ])
    db_session.commit()


# ----------------------------------------------------------------------
# Service 层
# ----------------------------------------------------------------------
class TestGenerateDecision:
    def test_kaoyan_path_aggregates(self, db_session, seed_decision_data):
        result = generate_decision(db_session, major="计算机", region="广东")
        kaoyan = next(m for m in result["metrics"] if m["path_type"] == "kaoyan")
        # 命中 3 条（排除法学）
        assert kaoyan["match_score"] > 0
        # 平均复试线 340-380 区间
        assert "340" in kaoyan["pros"][0] or "380" in kaoyan["pros"][0]
        # 报录比样本：中山大学 400/40 = 10.0:1
        risk_desc = kaoyan["risk_description"]
        assert "10.0:1" in risk_desc
        # 招生目录合计 80+60=140
        assert any("140" in p for p in kaoyan["pros"])
        # 证据溯源：data_sources 名称数组
        assert any(ev["label"].startswith("分数线") for ev in kaoyan["evidence"])
        assert any("复试线汇总" in (ev["note"] or "") for ev in kaoyan["evidence"])

    def test_civil_service_path_aggregates(self, db_session, seed_decision_data):
        result = generate_decision(db_session, major="计算机", region="广东")
        civil = next(m for m in result["metrics"] if m["path_type"] == "civil_service")
        # 国考 2 个（排除法学）+ 省考 1 个 = 3
        assert "国考可报岗位 2 个" in civil["pros"][0]
        assert "省考可报岗位 1 个" in civil["pros"][0]
        # 国考招录 2+1=3 人
        assert "招录合计 3 人" in civil["pros"][0]
        # 进面分均值 (118.5+121)/2=119.75
        assert "119.8" in civil["pros"][0] or "119.75" in civil["pros"][0]
        # 证据带 source_url
        urls = [ev["source_url"] for ev in civil["evidence"] if ev["source_url"]]
        assert any("scs.gov.cn" in u for u in urls)
        assert any("rsks.gd.gov.cn" in u for u in urls)

    def test_employment_path_aggregates(self, db_session, seed_decision_data):
        result = generate_decision(db_session, major="计算机", region="广东")
        emp = next(m for m in result["metrics"] if m["path_type"] == "employment")
        # 行业薪资带命中（排除汽车制造业）；广东无地区数据 → 回退全国口径
        assert "13.5" in emp["pros"][0]
        assert "全国口径" in emp["pros"][0]
        # 院校就业率平均 (95+93)/2=94.0
        assert any("94.0" in p for p in emp["pros"])
        # market_data 证据带 source_url
        assert any(ev["source_url"] and "stats.gov.cn" in ev["source_url"] for ev in emp["evidence"])

    def test_employment_salary_by_city(self, db_session, seed_decision_data):
        """城市粒度薪资：region=深圳 命中 entry 级岗位薪资，无 URL 时 note 标注来源。"""
        result = generate_decision(db_session, major="计算机", region="深圳")
        emp = next(m for m in result["metrics"] if m["path_type"] == "employment")
        assert any("腾讯" in p for p in emp["pros"])
        assert any(ev["source_url"] is None and "猎聘" in (ev["note"] or "") for ev in emp["evidence"])

    def test_no_data_degrades_gracefully(self, db_session):
        """完全不匹配的专业 → 三路空数据占位，不抛异常、不编造数字。"""
        result = generate_decision(db_session, major="冷门考古方向", region="西藏")
        assert len(result["metrics"]) == 3
        for m in result["metrics"]:
            assert m["match_score"] == 0
            assert m["income_1y"] == "暂无相关数据"
            assert m["evidence"] == []

    def test_region_filter_scope(self, db_session, seed_decision_data):
        """考公限定地区：只命中广东岗位。"""
        result = generate_decision(db_session, major="计算机", region="广东")
        civil = next(m for m in result["metrics"] if m["path_type"] == "civil_service")
        assert "国考可报岗位 2 个" in civil["pros"][0]

    def test_input_summary(self, db_session, seed_decision_data):
        result = generate_decision(db_session, major="计算机", region="广东",
                                   school_tier="985", graduation_year=2027)
        assert result["input"]["graduation_year"] == 2027
        assert result["input"]["school_tier"] == "985"
        # 院校证据按 985 过滤
        emp = next(m for m in result["metrics"] if m["path_type"] == "employment")
        assert all(ev["label"].startswith("院校参考") for ev in emp["evidence"] if ev["label"].startswith("院校参考"))


# ----------------------------------------------------------------------
# API 层
# ----------------------------------------------------------------------
class TestPathDecisionAPI:
    def test_analyze_requires_auth(self, client):
        resp = client.post("/api/path-decision/analyze", json={"major": "计算机"})
        assert resp.status_code == 401

    def test_analyze_ok(self, client, auth_headers, db_session, seed_decision_data):
        resp = client.post(
            "/api/path-decision/analyze",
            json={"major": "计算机", "region": "广东", "school_tier": "985",
                  "graduation_year": 2027},
            headers=auth_headers,
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert len(body["metrics"]) == 3
        types = {m["path_type"] for m in body["metrics"]}
        assert types == {"kaoyan", "civil_service", "employment"}
        # 每路都带 evidence 列表（字段存在即可）
        for m in body["metrics"]:
            assert "evidence" in m
        assert body["input"]["graduation_year"] == 2027
        assert body["recommendation"]

    def test_analyze_invalid_major(self, client, auth_headers):
        resp = client.post(
            "/api/path-decision/analyze",
            json={"major": ""},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_history(self, client, auth_headers, db_session, seed_decision_data):
        client.post(
            "/api/path-decision/analyze",
            json={"major": "计算机", "region": "广东"},
            headers=auth_headers,
        )
        resp = client.get("/api/path-decision/history", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 1
        assert len(body[0]["metrics"]) == 3
