# backend/tests/test_employment_market_overview.py
"""B4（2026-09-26 数据底座）：就业市场概览端点——companies/salary 真实聚合+覆盖度如实。"""

import pytest
from sqlalchemy.orm import Session

from app.models.company import Company, CompanySize
from app.models.salary_benchmark import SalaryBenchmark
from app.models.school import School
from app.services.employment_service import market_overview


@pytest.fixture
def seeded_market(db_session: Session):
    db_session.add_all(
        [
            Company(name="测试科技A", industry="信息传输、软件和信息技术服务业", size=CompanySize.large),
            Company(name="测试科技B", industry="信息传输、软件和信息技术服务业", size=CompanySize.medium),
            Company(name="测试银行C", industry="金融业", size=CompanySize.large),
            SalaryBenchmark(
                company="测试科技A", position="软件开发工程师", city="深圳市",
                experience_level="entry", salary_min=15, salary_median=20, salary_max=30,
                year=2025, source="测试源",
            ),
            SalaryBenchmark(
                company="测试科技B", position="前端开发工程师", city="广州市",
                experience_level="entry", salary_min=12, salary_median=16, salary_max=24,
                year=2025, source="测试源",
            ),
            School(name="就业率样本校", slug="sample-school", employment_rate=91.5, grad_school_rate=40.0),
        ]
    )
    db_session.commit()
    yield
    db_session.rollback()


def test_market_overview_aggregates_real_tables(db_session: Session, seeded_market):
    data = market_overview(db_session)
    assert data["company_total"] >= 3
    assert data["salary_total"] >= 2
    industries = {r["industry"]: r["count"] for r in data["top_industries"]}
    assert industries["信息传输、软件和信息技术服务业"] >= 2
    cities = {r["city"]: r for r in data["city_salary_bands"]}
    assert cities["深圳市"]["sample_count"] >= 1
    assert cities["深圳市"]["min_k"] == 15 and cities["深圳市"]["max_k"] == 30
    # 院校就业率只列有值的行，覆盖度如实（3 所院校中 1 所有值）
    samples = {s["name"]: s for s in data["school_employment_samples"]}
    assert samples["就业率样本校"]["employment_rate"] == 91.5
    assert data["school_employment_coverage"] >= 1


def test_market_overview_empty_db_is_honest(db_session: Session):
    """空库=全 0+空列表（诚实空态），不编数。"""
    data = market_overview(db_session)
    assert data["company_total"] == 0
    assert data["top_industries"] == []
    assert data["school_employment_samples"] == []
