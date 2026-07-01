# backend/tests/test_api_external_data.py
"""外部数据查询 API 测试 — 公司/薪资/市场数据。"""
import pytest

from app.models.company import Company, CompanySize
from app.models.market_data import MarketData
from app.models.salary_benchmark import ExperienceLevel, SalaryBenchmark
from app.seed.seed_companies import seed_companies
from app.seed.seed_market_data import seed_market_data
from app.seed.seed_salary_benchmarks import seed_salary_benchmarks


# ======================================================================
# 辅助函数
# ======================================================================

@pytest.fixture
def seeded_db(db_session):
    """加载全部种子数据到测试数据库。"""
    seed_companies(db_session)
    seed_salary_benchmarks(db_session)
    seed_market_data(db_session)
    return db_session


# ======================================================================
# 公司列表查询
# ======================================================================

class TestCompanies:
    def test_list_companies_default(self, seeded_db, client):
        """默认查询返回公司列表。"""
        resp = client.get("/api/companies")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 50
        # 验证字段完整性
        first = data[0]
        assert "id" in first
        assert "name" in first
        assert "industry" in first
        assert "size" in first

    def test_search_company_by_name(self, seeded_db, client):
        """按名称模糊搜索公司。"""
        resp = client.get("/api/companies", params={"name": "腾讯"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["name"] == "腾讯"

    def test_search_company_fuzzy(self, seeded_db, client):
        """模糊搜索（部分关键词）。"""
        resp = client.get("/api/companies", params={"name": "中"})
        assert resp.status_code == 200
        data = resp.json()
        names = [c["name"] for c in data]
        # 应包含含"中"的公司（中国银行/中金/中信/中石油/中石化/中兴/中芯等）
        assert "中国银行" in names
        assert "中金公司" in names

    def test_filter_by_industry(self, seeded_db, client):
        """按行业筛选公司。"""
        resp = client.get("/api/companies", params={"industry": "金融"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) > 0
        for c in data:
            assert c["industry"] == "金融"

    def test_limit_parameter(self, seeded_db, client):
        """limit 参数限制返回数量。"""
        resp = client.get("/api/companies", params={"limit": 5})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 5

    def test_no_auth_required(self, seeded_db, client):
        """公开接口不需要登录。"""
        resp = client.get("/api/companies")
        assert resp.status_code == 200

    def test_size_enum_serialized_as_string(self, seeded_db, client):
        """size 枚举应序列化为字符串值。"""
        resp = client.get("/api/companies", params={"name": "腾讯"})
        assert resp.status_code == 200
        data = resp.json()
        assert data[0]["size"] == "giant"


# ======================================================================
# 薪资基准查询
# ======================================================================

class TestSalaryBenchmarks:
    def test_list_salary_default(self, seeded_db, client):
        """默认查询返回薪资基准列表。"""
        resp = client.get("/api/salary-benchmarks")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) > 0
        first = data[0]
        assert "company" in first
        assert "position" in first
        assert "salary_min" in first
        assert "salary_median" in first
        assert "salary_max" in first

    def test_filter_by_company(self, seeded_db, client):
        """按公司筛选薪资基准。"""
        resp = client.get(
            "/api/salary-benchmarks", params={"company": "腾讯"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) > 0
        for s in data:
            assert "腾讯" in s["company"]

    def test_filter_by_position(self, seeded_db, client):
        """按岗位筛选薪资基准。"""
        resp = client.get(
            "/api/salary-benchmarks", params={"position": "后端开发"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) > 0
        for s in data:
            assert "后端开发" in s["position"]

    def test_filter_by_city(self, seeded_db, client):
        """按城市筛选薪资基准。"""
        resp = client.get("/api/salary-benchmarks", params={"city": "深圳"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) > 0
        for s in data:
            assert "深圳" in s["city"]

    def test_combined_filter(self, seeded_db, client):
        """组合筛选（公司+岗位+城市）。"""
        resp = client.get(
            "/api/salary-benchmarks",
            params={"company": "腾讯", "position": "后端开发", "city": "深圳"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) > 0
        for s in data:
            assert s["company"] == "腾讯"
            assert s["position"] == "后端开发"
            assert s["city"] == "深圳"

    def test_experience_level_serialized(self, seeded_db, client):
        """experience_level 枚举应序列化为字符串值。"""
        resp = client.get(
            "/api/salary-benchmarks",
            params={"company": "腾讯", "position": "后端开发", "city": "深圳"},
        )
        assert resp.status_code == 200
        data = resp.json()
        levels = {s["experience_level"] for s in data}
        assert levels.issubset({"entry", "junior", "mid", "senior", "lead"})

    def test_no_auth_required(self, seeded_db, client):
        """公开接口不需要登录。"""
        resp = client.get("/api/salary-benchmarks")
        assert resp.status_code == 200


# ======================================================================
# 市场数据查询
# ======================================================================

class TestMarketData:
    def test_list_market_data_default(self, seeded_db, client):
        """默认查询返回市场数据列表。"""
        resp = client.get("/api/market-data")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) > 0
        first = data[0]
        assert "indicator" in first
        assert "category" in first
        assert "value" in first
        assert "unit" in first
        assert "year" in first

    def test_filter_by_category(self, seeded_db, client):
        """按分类筛选市场数据。"""
        resp = client.get("/api/market-data", params={"category": "salary"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) > 0
        for m in data:
            assert m["category"] == "salary"

    def test_filter_by_year(self, seeded_db, client):
        """按年份筛选市场数据。"""
        resp = client.get("/api/market-data", params={"year": 2024})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) > 0
        for m in data:
            assert m["year"] == 2024

    def test_filter_by_industry(self, seeded_db, client):
        """按行业筛选市场数据。"""
        resp = client.get("/api/market-data", params={"industry": "金融"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) > 0
        for m in data:
            assert m["industry"] == "金融"

    def test_no_auth_required(self, seeded_db, client):
        """公开接口不需要登录。"""
        resp = client.get("/api/market-data")
        assert resp.status_code == 200


# ======================================================================
# 种子数据加载验证
# ======================================================================

class TestSeedDataLoaded:
    def test_companies_seed_loaded(self, seeded_db):
        """种子数据加载后公司数据存在。"""
        count = seeded_db.query(Company).count()
        assert count >= 50
        # 验证知名公司存在
        names = {c.name for c in seeded_db.query(Company).all()}
        for expected in ["腾讯", "阿里巴巴", "字节跳动", "华为", "工商银行", "微软", "国家电网", "大疆"]:
            assert expected in names, f"缺失公司: {expected}"

    def test_salary_benchmarks_seed_loaded(self, seeded_db):
        """种子数据加载后薪资基准数据存在。"""
        count = seeded_db.query(SalaryBenchmark).count()
        assert count >= 200
        # 验证覆盖多公司多岗位
        companies = {
            s.company for s in seeded_db.query(SalaryBenchmark).all()
        }
        assert len(companies) >= 20
        positions = {
            s.position for s in seeded_db.query(SalaryBenchmark).all()
        }
        assert len(positions) >= 10

    def test_market_data_seed_loaded(self, seeded_db):
        """种子数据加载后市场数据存在。"""
        count = seeded_db.query(MarketData).count()
        assert count >= 30
        # 验证覆盖多年份
        years = {m.year for m in seeded_db.query(MarketData).all()}
        assert 2022 in years
        assert 2023 in years
        assert 2024 in years
        # 验证来源标注
        sources = {m.source for m in seeded_db.query(MarketData).all()}
        assert "国家统计局" in sources

    def test_seed_idempotent(self, db_session):
        """种子脚本幂等：重复执行不产生重复数据。"""
        seed_companies(db_session)
        c1 = db_session.query(Company).count()
        # 再次执行
        inserted = seed_companies(db_session)
        c2 = db_session.query(Company).count()
        assert inserted == 0
        assert c1 == c2

        seed_salary_benchmarks(db_session)
        s1 = db_session.query(SalaryBenchmark).count()
        inserted_s = seed_salary_benchmarks(db_session)
        s2 = db_session.query(SalaryBenchmark).count()
        assert inserted_s == 0
        assert s1 == s2

        seed_market_data(db_session)
        m1 = db_session.query(MarketData).count()
        inserted_m = seed_market_data(db_session)
        m2 = db_session.query(MarketData).count()
        assert inserted_m == 0
        assert m1 == m2
