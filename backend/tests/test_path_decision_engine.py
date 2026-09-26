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
def _make_scoreline(
    university: str,
    major: str,
    year: int,
    score: int,
    application: int | None = None,
    enrollment: int | None = None,
):
    return GradScorelineRecord(
        university_name=university,
        major_name=major,
        year=year,
        total_score_line=score,
        application_count=application,
        enrollment_count=enrollment,
        data_sources=["scorelines_real_data.json:2026-07-12"],
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


def _make_gwy_position(
    id_suffix: str,
    *,
    position_code: str,
    major_req: str,
    work_location: str,
    recruit_count: int = 1,
    dept_name: str = "测试部门",
    position_name: str = "一级行政执法员",
    political_status: str = "不限",
    education_req: str = "本科及以上",
    grassroots_exp_req: str = "无限制",
    remarks: str | None = None,
):
    now = _utcnow()
    return GwyPosition(
        id=f"gwy-{id_suffix}",
        year=2026,
        exam_type="国考",
        dept_code=f"1301{id_suffix}",
        dept_name=dept_name,
        bureau="测试局",
        agency_type="省级以下直属机构",
        position_name=position_name,
        position_attr="普通职位",
        position_distribution="其他职位",
        position_desc="测试",
        position_code=position_code,
        org_level="县（区）级及以下",
        exam_category="行政执法类",
        recruit_count=recruit_count,
        major_req=major_req,
        education_req=education_req,
        degree_req="学士",
        political_status=political_status,
        min_work_years="无限制",
        grassroots_exp_req=grassroots_exp_req,
        professional_test="否",
        interview_ratio="3:1",
        work_location=work_location,
        settle_location=work_location,
        remarks=remarks,
        dept_website="http://example.gov.cn",
        phone1="010-12345678",
        phone2=None,
        phone3=None,
        sheet_name="省级以下直属机构",
        source_url="http://dl.scs.gov.cn/mock/positions.xlsx",
        created_at=now,
        updated_at=now,
    )


def _make_score_line(id_suffix: str, *, position_code: str, min_score: float):
    now = _utcnow()
    return GwyScoreLine(
        id=f"line-{id_suffix}",
        year=2026,
        batch="首批",
        dept_name="测试部门",
        dept_code="1301x",
        bureau="测试局",
        position_name="一级行政执法员",
        position_code=position_code,
        min_score=min_score,
        source_url="http://dl.scs.gov.cn/mock/score.xlsx",
        created_at=now,
        updated_at=now,
    )


def _make_province_position(
    id_suffix: str,
    *,
    position_code: str,
    major_req_undergrad: str,
    province: str = "广东",
    recruit_count: int = 1,
    education_req: str = "本科",
    fresh_grad_only: str = "是",
    grassroots_exp_req: str = "否",
):
    now = _utcnow()
    return GwyProvincePosition(
        id=f"prov-{id_suffix}",
        year=2026,
        province=province,
        dept_name="广东省测试局",
        dept_code=f"199{id_suffix}",
        position_name="一级科员",
        position_code=position_code,
        position_desc="测试",
        position_type="综合管理类",
        recruit_count=recruit_count,
        education_req=education_req,
        degree_req="学士",
        major_req_grad=None,
        major_req_undergrad=major_req_undergrad,
        major_req_junior=None,
        grassroots_exp_req=grassroots_exp_req,
        psych_test="否",
        fresh_grad_only=fresh_grad_only,
        other_requirements=None,
        exam_region="广州",
        sheet_name="乡镇机关",
        source_url="http://rsks.gd.gov.cn/mock/positions.xlsx",
        created_at=now,
        updated_at=now,
    )


def _make_market_data(
    indicator: str,
    industry: str,
    value: float,
    unit: str,
    year: int = 2025,
    region: str | None = "全国",
):
    return MarketData(
        indicator=indicator,
        category="宏观就业面",
        value=value,
        unit=unit,
        region=region,
        industry=industry,
        year=year,
        source="统计公报",
        source_url="http://www.stats.gov.cn/mock/report",
    )


def _make_salary(
    company: str, position: str, city: str, median: int, year: int = 2025, source: str = "猎聘"
):
    return SalaryBenchmark(
        company=company,
        position=position,
        city=city,
        experience_level=ExperienceLevel.entry,
        salary_min=median - 5,
        salary_median=median,
        salary_max=median + 5,
        source=source,
        year=year,
    )


def _make_school(name: str, province: str, level: str, emp_rate: float, grad_rate: float):
    return School(
        name=name,
        slug=f"slug-{name}",
        code="10001",
        province=province,
        level=level,
        ranking=100,
        employment_rate=emp_rate,
        grad_school_rate=grad_rate,
    )


# ----------------------------------------------------------------------
# Seed fixture
# ----------------------------------------------------------------------
@pytest.fixture
def seed_decision_data(db_session):
    """写入三路数据，全部与「计算机 / 广东」匹配。"""
    db_session.add_all(
        [
            # 考研路
            _make_scoreline("中山大学", "计算机技术", 2025, 350, application=400, enrollment=40),
            _make_scoreline("华南理工大学", "计算机技术", 2024, 340),
            _make_scoreline("北京大学", "计算机科学与技术", 2025, 380),
            _make_scoreline("中山大学", "法学", 2025, 360),  # 不匹配专业
            _make_yz("中山大学", "计算机技术", 80),
            _make_yz("华南理工大学", "计算机技术", 60),
            # 考公路（国考 2026 广东）
            _make_gwy_position(
                "1",
                position_code="1301001",
                major_req="计算机类",
                work_location="广东省广州市天河区",
                recruit_count=2,
            ),
            _make_gwy_position(
                "2",
                position_code="1301002",
                major_req="计算机类",
                work_location="广东省深圳市南山区",
                recruit_count=1,
            ),
            _make_gwy_position(
                "3", position_code="1301003", major_req="法学", work_location="广东省广州市天河区"
            ),  # 不匹配专业
            _make_score_line("1", position_code="1301001", min_score=118.5),
            _make_score_line("2", position_code="1301002", min_score=121.0),
            # 考公路（省考广东 2026）
            _make_province_position(
                "1", position_code="199001", major_req_undergrad="计算机类", recruit_count=3
            ),
            # 就业路
            _make_market_data(
                "城镇单位就业人员平均工资", "计算机、通信和其他电子设备制造业", 13.5, "万元"
            ),
            _make_market_data("规模以上工业企业利润总额", "汽车制造业", 5000, "亿元"),  # 不匹配
            _make_salary("腾讯", "后台开发工程师", "深圳", 20),
            _make_school("中山大学", "广东", "985", 95.0, 40.0),
            _make_school("华南理工大学", "广东", "985", 93.0, 38.0),
        ]
    )
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
        assert any("scorelines_real_data.json" in (ev["note"] or "") for ev in kaoyan["evidence"])

    def test_employment_path_aggregates(self, db_session, seed_decision_data):
        result = generate_decision(db_session, major="计算机", region="广东")
        emp = next(m for m in result["metrics"] if m["path_type"] == "employment")
        # 行业薪资带命中（排除汽车制造业）；广东无地区数据 → 回退全国口径
        assert "13.5" in emp["pros"][0]
        assert "全国口径" in emp["pros"][0]
        # 院校就业率平均 (95+93)/2=94.0
        assert any("94.0" in p for p in emp["pros"])
        # market_data 证据带 source_url
        assert any(
            ev["source_url"] and "stats.gov.cn" in ev["source_url"] for ev in emp["evidence"]
        )

    def test_employment_salary_by_city(self, db_session, seed_decision_data):
        """城市粒度薪资：region=深圳 命中 entry 级岗位薪资，无 URL 时 note 标注来源。"""
        result = generate_decision(db_session, major="计算机", region="深圳")
        emp = next(m for m in result["metrics"] if m["path_type"] == "employment")
        assert any("腾讯" in p for p in emp["pros"])
        assert any(
            ev["source_url"] is None and "猎聘" in (ev["note"] or "") for ev in emp["evidence"]
        )

    def test_no_data_degrades_gracefully(self, db_session):
        """完全不匹配的专业 → 三路空数据占位，不抛异常、不编造数字。"""
        result = generate_decision(db_session, major="冷门考古方向", region="西藏")
        assert len(result["metrics"]) == 2
        for m in result["metrics"]:
            assert m["match_score"] == 0
            assert m["income_1y"] == "暂无相关数据"
            assert m["evidence"] == []

    def test_input_summary(self, db_session, seed_decision_data):
        result = generate_decision(
            db_session, major="计算机", region="广东", school_tier="985", graduation_year=2027
        )
        assert result["input"]["graduation_year"] == 2027
        assert result["input"]["school_tier"] == "985"
        # 院校证据按 985 过滤
        emp = next(m for m in result["metrics"] if m["path_type"] == "employment")
        assert all(
            ev["label"].startswith("院校参考")
            for ev in emp["evidence"]
            if ev["label"].startswith("院校参考")
        )


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
            json={
                "major": "计算机",
                "region": "广东",
                "school_tier": "985",
                "graduation_year": 2027,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert len(body["metrics"]) == 2
        types = {m["path_type"] for m in body["metrics"]}
        assert types == {"kaoyan", "employment"}
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
        assert len(body[0]["metrics"]) == 2


# ----------------------------------------------------------------------
# 个人条件可报边界（决策飞轮第一圈）— service 层
# ----------------------------------------------------------------------
@pytest.fixture
def seed_personal_filter_data(db_session):
    """个人条件过滤专用数据：
    A 党员+硕士+限应届；B 不限党+仅限博士+限男性；C 党员+本科及以上+非应届+需基层经历；
    D 同一 position_code 两行（position_code 去重）；省考 E 限应届+需基层；省考 F 全开放。
    """
    db_session.add_all(
        [
            _make_gwy_position(
                "p1",
                position_code="1302001",
                major_req="计算机类",
                work_location="广东省广州市",
                political_status="中共党员",
                education_req="硕士",
                grassroots_exp_req="无限制",
                remarks="限应届",
            ),
            _make_gwy_position(
                "p2",
                position_code="1302002",
                major_req="计算机类",
                work_location="广东省深圳市",
                political_status="不限",
                education_req="仅限博士",
                remarks="限男性",
            ),
            _make_gwy_position(
                "p3",
                position_code="1302003",
                major_req="计算机类",
                work_location="广东省佛山市",
                political_status="中共党员",
                education_req="本科及以上",
                grassroots_exp_req="基层工作最低年限2年",
                remarks="非应届高校毕业生可报",
            ),
            # 同一 position_code 两行 → 去重后只算 1 个岗位
            _make_gwy_position(
                "p4a",
                position_code="1302004",
                major_req="计算机类",
                work_location="广东省珠海市",
                position_name="一级行政执法员（一）",
            ),
            _make_gwy_position(
                "p4b",
                position_code="1302004",
                major_req="计算机类",
                work_location="广东省珠海市",
                position_name="一级行政执法员（二）",
            ),
            _make_province_position(
                "p1",
                position_code="199101",
                major_req_undergrad="计算机类",
                fresh_grad_only="是",
                grassroots_exp_req="是",
            ),
            _make_province_position(
                "p2",
                position_code="199102",
                major_req_undergrad="计算机类",
                fresh_grad_only="否",
                grassroots_exp_req="否",
            ),
        ]
    )
    db_session.commit()


class TestKaoyanAvoidSchools:
    """考研院校劝退卡 — 模考估分显著低于复试线的院校诚实拒绝。"""

    def test_avoid_schools_triggered_with_alternatives(self, db_session, seed_decision_data):
        """seed：中山 350 / 华工 340 / 北大 380。est=300 → 北大低 80、中山低 50 劝退，华工低 40 劝退。"""
        result = generate_decision(
            db_session, major="计算机", region="广东", kaoyan_estimated_score=300
        )
        sa = result["school_analysis"]
        names = {a["university_name"] for a in sa["avoid_schools"]}
        assert names == {"北京大学", "中山大学", "华南理工大学"}
        pk = next(a for a in sa["avoid_schools"] if a["university_name"] == "北京大学")
        assert pk["verdict"] == "建议放弃"
        assert "复试线 380" in pk["basis"] and "低 80 分" in pk["basis"]
        assert "不等于录取线" in pk["confidence"]
        # 替代建议来自估分高于其复试线的院校——全部低于 300 时为空
        assert all(a["alternatives"] == [] for a in sa["avoid_schools"])

    def test_avoid_schools_boundary(self, db_session, seed_decision_data):
        """阈值边界：est=310 时华工(340) 低 30 → 触发；est=311 时低 29 → 不触发。"""
        edge = generate_decision(
            db_session, major="计算机", region="广东", kaoyan_estimated_score=310
        )
        avoided = {a["university_name"] for a in edge["school_analysis"]["avoid_schools"]}
        assert "华南理工大学" in avoided

        safe = generate_decision(
            db_session, major="计算机", region="广东", kaoyan_estimated_score=311
        )
        assert "华南理工大学" not in {
            a["university_name"] for a in safe["school_analysis"]["avoid_schools"]
        }

    def test_avoid_schools_with_alternatives(self, db_session, seed_decision_data):
        """est=345：只有北大（380，低 35）被劝退；替代建议含估分达线的华工（340）。"""
        result = generate_decision(
            db_session, major="计算机", region="广东", kaoyan_estimated_score=345
        )
        sa = result["school_analysis"]
        assert {a["university_name"] for a in sa["avoid_schools"]} == {"北京大学"}
        alts = sa["avoid_schools"][0]["alternatives"]
        assert len(alts) == 1
        assert "复试线 340" in alts[0]

    def test_no_est_keeps_avoid_schools_empty(self, db_session, seed_decision_data):
        """未填考研估分：不出劝退卡（向后兼容）。"""
        result = generate_decision(db_session, major="计算机", region="广东")
        assert result["school_analysis"]["avoid_schools"] == []


class TestSchoolAnalysis:
    def test_school_analysis_structure(self, db_session, seed_decision_data):
        """3 所命中院校（中山/华工/北大）触发分档；带覆盖率说明与来源。"""
        result = generate_decision(db_session, major="计算机", region="广东")
        sa = result["school_analysis"]
        assert sa is not None
        assert sa["matched_school_count"] == 3
        assert "基于现有复试线数据" in sa["coverage_note"]
        competitions = {i["competition"] for i in sa["items"]}
        assert competitions == {"偏高", "中等"}  # 北大 380 偏高；中山 350 / 华工 340 中等
        for item in sa["items"]:
            assert item["intel"] is None  # seed 无院校情报
            assert item["score_line"] in (350, 340, 380)
            assert item["source_url"] == "scorelines_real_data.json:2026-07-12"
        # 报录比：中山 400/40 = 10.0:1
        zsu = next(i for i in sa["items"] if i["university_name"] == "中山大学")
        assert zsu["ratio"] == "10.0:1"

    def test_small_sample_all_medium(self, db_session, seed_decision_data):
        """命中 1 所院校 → 不强行分档，全部标"中等"并带覆盖说明。"""
        result = generate_decision(db_session, major="法学", region="广东")
        sa = result["school_analysis"]
        assert sa["matched_school_count"] == 1
        assert sa["items"][0]["competition"] == "中等"
        assert sa["items"][0]["university_name"] == "中山大学"

    def test_intel_summary_non_ai_first(self, db_session, seed_decision_data):
        """院校有真实情报时优先生效并可读；AI 生成行显式标注。"""
        from uuid import uuid4

        from app.models.grad_intel import GradSchoolIntel

        db_session.add(
            GradSchoolIntel(
                user_id=uuid4(),
                school_name="中山大学",
                major_name="计算机技术",
                school_tier="985",
                year=2026,
                background_discrimination="none",
                first_choice_protection="yes",
                admission_ratio="10:1",
                is_ai_generated=False,
            )
        )
        db_session.commit()
        result = generate_decision(db_session, major="计算机", region="广东")
        zsu = next(
            i for i in result["school_analysis"]["items"] if i["university_name"] == "中山大学"
        )
        assert zsu["intel"] == "不卡第一学历；保护一志愿；报录比约 10:1"


# ----------------------------------------------------------------------
# 个人条件 + 结果回传 — API 层
# ----------------------------------------------------------------------
class TestPersonalAndOutcomeAPI:
    def test_analyze_with_personal_conditions(
        self, client, auth_headers, db_session, seed_decision_data
    ):
        resp = client.post(
            "/api/path-decision/analyze",
            json={
                "major": "计算机",
                "region": "广东",
                "fresh_status": "应届",
                "party_status": "中共党员",
                "education": "本科",
                "gender": "男",
                "estimated_score": 135,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["position_analysis"] is None  # 考公路 2026-09-26 退役，岗位级分析不再产出
        assert body["school_analysis"]["matched_school_count"] == 3
        assert body["recommendation"].startswith("以你的条件")
        assert body["input"]["estimated_score"] == 135

    def test_analyze_without_region_does_not_crash(
        self, client, auth_headers, db_session, seed_decision_data
    ):
        """回归：不指定地区时岗位薪资样本被跳过，不得对已 limit(0) 的查询再 order_by。"""
        resp = client.post(
            "/api/path-decision/analyze",
            json={"major": "计算机"},
            headers=auth_headers,
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert len(body["metrics"]) == 2
        assert body["input"]["region"] == "全国"

    def test_analyze_rejects_out_of_range_score(self, client, auth_headers):
        resp = client.post(
            "/api/path-decision/analyze",
            json={"major": "计算机", "estimated_score": 250},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_outcome_requires_auth(self, client, auth_headers, db_session, seed_decision_data):
        resp = client.post(
            "/api/path-decision/analyze",
            json={"major": "计算机", "region": "广东"},
            headers=auth_headers,
        )
        rid = resp.json()["id"]
        noauth = client.post(
            f"/api/path-decision/{rid}/outcome",
            json={"selected_path": "civil_service", "outcome_status": "following"},
        )
        assert noauth.status_code == 401

    def test_outcome_submit_roundtrip(self, client, auth_headers, db_session, seed_decision_data):
        resp = client.post(
            "/api/path-decision/analyze",
            json={"major": "计算机", "region": "广东"},
            headers=auth_headers,
        )
        rid = resp.json()["id"]
        out = client.post(
            f"/api/path-decision/{rid}/outcome",
            json={
                "selected_path": "civil_service",
                "selected_label": "省考行政执法岗",
                "outcome_status": "following",
                "actual_outcome": "已报名 26 省考",
                "satisfaction": 4,
            },
            headers=auth_headers,
        )
        assert out.status_code == 200, out.text
        body = out.json()
        assert body["outcome"]["selected_path"] == "civil_service"
        assert body["outcome"]["selected_label"] == "省考行政执法岗"
        assert body["outcome"]["outcome_status"] == "following"
        assert body["outcome"]["actual_outcome"] == "已报名 26 省考"
        assert body["outcome"]["satisfaction"] == 4
        assert body["outcome"]["reviewed_at"]
        # 历史记录应带 outcome
        hist = client.get("/api/path-decision/history", headers=auth_headers)
        assert hist.json()[0]["outcome"]["outcome_status"] == "following"

    def test_outcome_stats_requires_auth(self, client):
        resp = client.get("/api/path-decision/outcome-stats")
        assert resp.status_code == 401

    def test_outcome_stats_aggregates(self, client, auth_headers, db_session, seed_decision_data):
        """回传统计：两条记录分别回传 → 总数与分布正确（匿名聚合，跨用户）。"""
        for path, status in [("civil_service", "following"), ("kaoyan", "achieved")]:
            resp = client.post(
                "/api/path-decision/analyze",
                json={"major": "计算机", "region": "广东"},
                headers=auth_headers,
            )
            rid = resp.json()["id"]
            out = client.post(
                f"/api/path-decision/{rid}/outcome",
                json={"selected_path": path, "outcome_status": status},
                headers=auth_headers,
            )
            assert out.status_code == 200, out.text

        stats = client.get("/api/path-decision/outcome-stats", headers=auth_headers)
        assert stats.status_code == 200, stats.text
        body = stats.json()
        assert body["total_outcomes"] == 2
        assert body["by_status"]["following"] == 1
        assert body["by_status"]["achieved"] == 1
        assert body["by_selected_path"]["civil_service"] == 1
        assert body["by_selected_path"]["kaoyan"] == 1

    def test_outcome_not_owned_404(self, client, auth_headers, db_session, seed_decision_data):
        resp = client.post(
            "/api/path-decision/analyze",
            json={"major": "计算机", "region": "广东"},
            headers=auth_headers,
        )
        rid = resp.json()["id"]
        # 第二个用户尝试回写他人记录 → 404
        client.post(
            "/api/auth/register",
            json={"email": "other@example.com", "password": "Test1234!", "name": "另一位"},
        )
        login = client.post(
            "/api/auth/login",
            json={"email": "other@example.com", "password": "Test1234!"},
        )
        other_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        bad = client.post(
            f"/api/path-decision/{rid}/outcome",
            json={"selected_path": "kaoyan", "outcome_status": "achieved"},
            headers=other_headers,
        )
        assert bad.status_code == 404

    def test_outcome_invalid_status_422(self, client, auth_headers, db_session, seed_decision_data):
        resp = client.post(
            "/api/path-decision/analyze",
            json={"major": "计算机", "region": "广东"},
            headers=auth_headers,
        )
        rid = resp.json()["id"]
        bad = client.post(
            f"/api/path-decision/{rid}/outcome",
            json={"selected_path": "civil_service", "outcome_status": "unknown_xxx"},
            headers=auth_headers,
        )
        assert bad.status_code == 422


# ----------------------------------------------------------------------
# R-01（spec 011 信任对齐第一批）：recommendation 任何输入组合下
# 不含退役考公路文案；个人条件行保留（两路口径，考研估分语义保留）
# ----------------------------------------------------------------------
class TestTrustAlignmentR01:
    RETIRED_WORDS = ["考公", "行测", "申论", "岗位分析", "可报边界", "三条路", "三路"]

    def _analyze(self, client, auth_headers, payload: dict) -> dict:
        resp = client.post(
            "/api/path-decision/analyze", json=payload, headers=auth_headers
        )
        assert resp.status_code == 200, resp.text
        return resp.json()

    def test_full_conditions_recommendation_clean(
        self, client, auth_headers, db_session, seed_decision_data
    ):
        body = self._analyze(
            client,
            auth_headers,
            {
                "major": "计算机",
                "region": "广东",
                "fresh_status": "应届",
                "party_status": "中共党员",
                "education": "本科",
                "gender": "男",
                "has_grassroots": True,
                "estimated_score": 135,
            },
        )
        rec = body["recommendation"]
        for w in self.RETIRED_WORDS:
            assert w not in rec, f"recommendation 含退役词「{w}」: {rec}"
        assert rec.startswith("以你的条件")  # 个人条件行保留（两路口径）

    def test_kaoyan_estimate_semantics_kept(
        self, client, auth_headers, db_session, seed_decision_data
    ):
        body = self._analyze(
            client,
            auth_headers,
            {"major": "计算机", "region": "广东", "kaoyan_estimated_score": 345},
        )
        rec = body["recommendation"]
        for w in self.RETIRED_WORDS:
            assert w not in rec, f"recommendation 含退役词「{w}」: {rec}"
        assert "预估考研初试 345 分" in rec  # 考研估分语义保留

    def test_minimal_input_recommendation_clean(
        self, client, auth_headers, db_session, seed_decision_data
    ):
        body = self._analyze(client, auth_headers, {"major": "会计学"})
        for w in self.RETIRED_WORDS:
            assert w not in body["recommendation"], (
                f"recommendation 含退役词「{w}」: {body['recommendation']}"
            )

