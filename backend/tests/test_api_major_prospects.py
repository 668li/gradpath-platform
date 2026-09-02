# backend/tests/test_api_major_prospects.py
"""专业前景 API 测试 — 聚合映射、行业/岗位薪资、去向公司、考研路径、兜底逻辑。"""

from app.models.company import Company, CompanySize
from app.models.grad_intel import GradSchoolIntel
from app.models.market_data import MarketData
from app.models.salary_benchmark import ExperienceLevel, SalaryBenchmark
from app.models.user import User
from app.services.major_prospect_service import MAJOR_MAP, list_majors, resolve_major


def _seed(db_session):
    user = User(email="crawler@example.com", name="数据爬虫", password_hash="x")
    db_session.add(user)
    db_session.commit()

    # 行业薪资：信息行业 2025 最新（非私营 24w / 私营 12w），制造业旧年份应被忽略
    db_session.add(
        MarketData(
            indicator="城镇非私营单位就业人员年平均工资",
            category="行业",
            value=238966,
            unit="元/年",
            industry="信息传输、软件和信息技术服务业",
            year=2024,
            source="国家统计局",
        )
    )
    db_session.add(
        MarketData(
            indicator="城镇私营单位就业人员年平均工资",
            category="行业",
            value=123193,
            unit="元/年",
            industry="信息传输、软件和信息技术服务业",
            year=2024,
            source="国家统计局",
        )
    )
    db_session.add(
        MarketData(
            indicator="城镇非私营单位就业人员年平均工资",
            category="行业",
            value=107987,
            unit="元/年",
            industry="制造业",
            year=2024,
            source="国家统计局",
        )
    )
    # 脏数据：score_line=0 占位（已知坑，必须过滤）
    db_session.add(
        GradSchoolIntel(
            user_id=user.id,
            school_name="清华大学",
            major_name="计算机科学与技术",
            school_tier="985",
            year=2026,
            admission_ratio="20:1",
            score_line=380,
        )
    )
    db_session.add(
        GradSchoolIntel(
            user_id=user.id,
            school_name="测试大学",
            major_name="计算机科学与技术",
            school_tier="211",
            year=2026,
            admission_ratio="3:1",
            score_line=0,
        )
    )
    # 出身个性化用：severe（卡第一学历）与 none（不卡）两条，验证排序与注解
    db_session.add(
        GradSchoolIntel(
            user_id=user.id,
            school_name="出身敏感大学",
            major_name="计算机科学与技术",
            school_tier="985",
            year=2026,
            admission_ratio="10:1",
            score_line=390,
            background_discrimination="severe",
        )
    )
    db_session.add(
        GradSchoolIntel(
            user_id=user.id,
            school_name="出身友好大学",
            major_name="计算机科学与技术",
            school_tier="211",
            year=2026,
            admission_ratio="5:1",
            score_line=360,
            background_discrimination="none",
        )
    )
    db_session.add(
        SalaryBenchmark(
            company="广州市人社局市场价位",
            position="软件和信息技术服务人员",
            city="广州",
            experience_level=ExperienceLevel.mid,
            salary_min=90000,
            salary_median=170885,
            salary_max=260000,
            source="广州市人社局市场价位",
            year=2024,
        )
    )
    db_session.add(
        SalaryBenchmark(
            company="杭州市人社局市场价位",
            position="软件和信息技术服务人员",
            city="杭州",
            experience_level=ExperienceLevel.mid,
            salary_min=80000,
            salary_median=150000,
            salary_max=230000,
            source="杭州市人社局市场价位",
            year=2024,
        )
    )
    db_session.add(
        Company(
            name="华为技术有限公司",
            industry="信息技术",
            size=CompanySize.giant,
            headquarters="深圳",
        )
    )
    db_session.add(
        Company(
            name="小米科技",
            industry="互联网",
            size=CompanySize.large,
            headquarters="北京",
        )
    )
    db_session.commit()


def test_resolve_major_exact_and_fuzzy():
    name, entry = resolve_major("计算机科学与技术")
    assert name == "计算机科学与技术" and entry is not None and entry.category == "工学"
    # 子串匹配：方向后缀 / 简称都能命中
    assert resolve_major("会计学")[1] is not None
    assert resolve_major("计算机（大数据方向）")[0] == "计算机科学与技术"
    # 完全未知专业返回 None
    assert resolve_major("赛博朋克工程")[1] is None


def test_major_map_has_no_duplicate_or_dirty_keys():
    # dict 本身保证唯一，这里验证主干专业都在且字段完整
    assert len(MAJOR_MAP) >= 50
    for name, entry in MAJOR_MAP.items():
        assert entry.category, name
        assert entry.civil_service in ("high", "medium", "low"), name
        assert entry.civil_note, name


def test_list_majors_includes_grad_intel_only_majors(db_session):
    _seed(db_session)
    majors = list_majors(db_session)
    names = {m["name"] for m in majors}
    assert "计算机科学与技术" in names
    assert len(majors) >= 50


def test_get_prospect_computer_science(db_session):
    _seed(db_session)
    from app.services.major_prospect_service import get_prospect

    p = get_prospect(db_session, "计算机科学与技术")
    assert p["exact_match"] is True
    assert p["category"] == "工学"
    # 行业薪资：信息行业最新年份非私营/私营口径拆分正确
    industries = {i["industry"]: i for i in p["industries"]}
    it = industries["信息传输、软件和信息技术服务业"]
    assert it["salary_non_private"] == 238966
    assert it["salary_private"] == 123193
    # 制造业也在计算机映射里
    assert "制造业" in industries
    # 岗位薪资：命中"软件"关键词
    assert any("软件" in x["position"] for x in p["positions"])
    # 公司：信息技术/互联网关键词命中
    company_names = {c["name"] for c in p["companies"]}
    assert "华为技术有限公司" in company_names
    # 考研：命中清华；score_line=0 脏数据被过滤
    paths = {g["school_name"]: g for g in p["grad_paths"]}
    assert "清华大学" in paths
    assert "测试大学" not in paths
    assert paths["清华大学"]["score_line"] == 380
    # 考公
    assert p["civil_service"]["level"] in ("high", "medium", "low")
    assert p["civil_service"]["note"]


def test_get_prospect_hanyu_fallback_alias(db_session):
    _seed(db_session)
    from app.services.major_prospect_service import get_prospect

    # 汉语言文学有独立映射条目，考公 high，考研别名连到中国语言文学
    p = get_prospect(db_session, "汉语言文学")
    assert p["matched_major"] == "汉语言文学"
    assert p["civil_service"]["level"] == "high"
    assert p["category"] == "文学"


def test_get_prospect_unknown_major_category_fallback(db_session):
    _seed(db_session)
    from app.services.major_prospect_service import get_prospect

    p = get_prospect(db_session, "智慧交通")
    assert p["exact_match"] is False
    assert p["category"] == "工学"  # 关键词推断
    # 兜底也有行业数据（制造业）
    assert any(i["industry"] == "制造业" for i in p["industries"])
    assert p["data_notes"]  # 溯源说明始终返回


def test_api_majors_and_detail(client, db_session):
    _seed(db_session)
    resp = client.get("/api/major-prospects/majors")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) >= 50
    assert {"name", "category", "source", "has_grad_intel"} <= set(items[0].keys())

    resp = client.get("/api/major-prospects/detail", params={"major": "计算机科学与技术"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["matched_major"] == "计算机科学与技术"
    assert data["industries"] and data["grad_paths"]

    # 空专业名 422
    resp = client.get("/api/major-prospects/detail", params={"major": "  "})
    assert resp.status_code == 422


def test_outgoing_tiers_endpoint(client):
    resp = client.get("/api/major-prospects/outgoing-tiers")
    assert resp.status_code == 200
    tiers = resp.json()["tiers"]
    assert tiers == ["985", "211", "双一流", "一本", "二本", "专科"]
    assert "专科" in tiers  # 覆盖专科出身（手动选档，不建专科院校库）


def test_grad_paths_sorted_by_score_without_tier(db_session):
    _seed(db_session)
    from app.services.major_prospect_service import get_prospect

    # 未传出身层次 → 纯分数线降序；且不产生个性化字段副作用
    p = get_prospect(db_session, "计算机科学与技术")
    assert p["grad_personalized"] is False
    order = [g["school_name"] for g in p["grad_paths"]]
    # 出身敏感(390)/清华(380)/出身友好(360) 按分数降序
    assert order.index("出身敏感大学") < order.index("清华大学") < order.index("出身友好大学")
    for g in p["grad_paths"]:
        assert g["outgoing_risk"] is None
        assert g["outgoing_note"] is None


def test_grad_paths_outgoing_tier_zhuanke_personalizes(db_session):
    _seed(db_session)
    from app.services.major_prospect_service import get_prospect

    # 专科出身 → 出身友好校前置，severe 目标校降权并标 high
    p = get_prospect(db_session, "计算机科学与技术", outgoing_tier="专科")
    assert p["grad_personalized"] is True
    assert p["tier_fact"]  # 出身层次制度性事实始终返回

    by_name = {g["school_name"]: g for g in p["grad_paths"]}
    friend = by_name["出身友好大学"]
    sensitive = by_name["出身敏感大学"]
    assert friend["outgoing_risk"] == "friendly"
    assert sensitive["outgoing_risk"] == "high"
    assert "友好" in friend["outgoing_note"]
    assert "风险偏高" in sensitive["outgoing_note"]

    order = [g["school_name"] for g in p["grad_paths"]]
    # friendly 排 severe 之前，即便 severe 分数更高
    assert order.index("出身友好大学") < order.index("出身敏感大学")


def test_grad_paths_outgoing_tier_985_not_downgraded(db_session):
    _seed(db_session)
    from app.services.major_prospect_service import get_prospect

    # 985 出身 → 不降权、不标注高险，维持分数线降序
    p = get_prospect(db_session, "计算机科学与技术", outgoing_tier="985")
    order = [g["school_name"] for g in p["grad_paths"]]
    assert order.index("出身敏感大学") < order.index("清华大学") < order.index("出身友好大学")
    sensitive = {g["school_name"]: g for g in p["grad_paths"]}["出身敏感大学"]
    assert sensitive["outgoing_risk"] is None


def test_api_detail_with_outgoing_tier(client, db_session):
    _seed(db_session)
    resp = client.get(
        "/api/major-prospects/detail",
        params={"major": "计算机科学与技术", "outgoing_tier": "专科"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["grad_personalized"] is True
    assert "tier_fact" in data and data["tier_fact"]
    by_name = {g["school_name"]: g for g in data["grad_paths"]}
    assert by_name["出身友好大学"]["outgoing_risk"] == "friendly"
    assert by_name["出身敏感大学"]["outgoing_risk"] == "high"
