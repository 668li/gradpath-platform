# backend/tests/test_api_employment.py
import pytest
from sqlalchemy import event

from app.models.school import School
from app.models.report_record import ReportRecord, ParseStatus
from app.models.employment_data import EmploymentData, Degree
from app.services.employment_service import get_stats, list_majors, list_schools


def _seed_employment_data(db_session):
    """创建测试种子数据"""
    school = School(name="清华大学", slug="tsinghua", code="10003")
    db_session.add(school)
    db_session.commit()

    for year in [2023, 2024]:
        report = ReportRecord(
            school_id=school.id, year=year, source_url=f"url-{year}",
            parse_status=ParseStatus.published,
        )
        db_session.add(report)
        db_session.commit()
        db_session.add(EmploymentData(
            report_id=report.id, major="机械工程", degree=Degree.bachelor,
            total_graduates=120, employment_rate=0.45 + (2024 - year) * 0.05,
            further_study_rate=0.35, civil_service_rate=0.10, abroad_rate=0.10,
            employer_ranking=[{"name": "三一重工", "count": 15}, {"name": "比亚迪", "count": 12}],
            industry_distribution={"制造业": 0.4, "互联网": 0.2},
            destination_region={"北京": 0.3, "上海": 0.15},
            school_for_further_study=[{"name": "清华大学", "count": 20}],
        ))
        db_session.commit()

    # 未发布的报告不应出现在搜索结果
    unpublished = ReportRecord(
        school_id=school.id, year=2022, source_url="url-2022",
        parse_status=ParseStatus.parsed,
    )
    db_session.add(unpublished)
    db_session.commit()
    db_session.add(EmploymentData(
        report_id=unpublished.id, major="机械工程", degree=Degree.bachelor,
        total_graduates=100, employment_rate=0.50,
    ))
    db_session.commit()


class TestEmploymentSearch:
    def test_search_by_school_and_major(self, client, db_session):
        _seed_employment_data(db_session)
        resp = client.get("/api/employment/search?school=清华&major=机械")
        assert resp.status_code == 200
        data = resp.json()
        assert data["school"]["name"] == "清华大学"
        assert "机械" in data["major"]
        assert len(data["records"]) == 2  # 2023 + 2024
        assert data["records"][0]["year"] == 2024  # 降序

    def test_search_with_year_filter(self, client, db_session):
        _seed_employment_data(db_session)
        resp = client.get("/api/employment/search?school=清华&major=机械&year=2024")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["records"]) == 1
        assert data["records"][0]["year"] == 2024

    def test_search_trend(self, client, db_session):
        _seed_employment_data(db_session)
        resp = client.get("/api/employment/search?school=清华&major=机械")
        data = resp.json()
        assert "trend" in data
        assert data["trend"]["years"] == [2023, 2024]  # 升序
        assert len(data["trend"]["employment_rate"]) == 2

    def test_search_excludes_unpublished(self, client, db_session):
        _seed_employment_data(db_session)
        resp = client.get("/api/employment/search?school=清华&major=机械")
        data = resp.json()
        years = [r["year"] for r in data["records"]]
        assert 2022 not in years  # 未发布的不出现

    def test_search_no_result(self, client, db_session):
        _seed_employment_data(db_session)
        resp = client.get("/api/employment/search?school=不存在&major=机械")
        assert resp.status_code == 200
        data = resp.json()
        assert data["records"] == []
        assert data["school"] is None


class TestEmploymentSchools:
    def test_list_schools(self, client, db_session):
        _seed_employment_data(db_session)
        resp = client.get("/api/employment/schools")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["name"] == "清华大学"
        assert data[0]["report_count"] == 2  # 只有 published 的


class TestEmploymentStats:
    def test_stats(self, client, db_session):
        _seed_employment_data(db_session)
        resp = client.get("/api/employment/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["school_count"] == 1
        assert data["report_count"] == 2  # 只算 published
        assert data["major_count"] >= 1


# ----------------------------------------------------------------------
# 辅助种子数据：多所学校（清华、北大有已发布报告；复旦无）
# ----------------------------------------------------------------------
def _seed_multi_schools(db_session):
    schools = []
    for idx, name in enumerate(["清华大学", "北京大学", "复旦大学"], start=1):
        school = School(name=name, slug=f"slug-{idx}", code=f"{idx:05d}")
        db_session.add(school)
        db_session.commit()
        schools.append(school)
        if name == "复旦大学":
            # 复旦大学没有已发布报告，不应出现在 list_schools
            continue
        for year in [2023, 2024]:
            report = ReportRecord(
                school_id=school.id,
                year=year,
                source_url=f"url-{idx}-{year}",
                parse_status=ParseStatus.published,
            )
            db_session.add(report)
            db_session.commit()
            db_session.add(
                EmploymentData(
                    report_id=report.id,
                    major=f"专业{idx}",
                    degree=Degree.bachelor,
                    total_graduates=100,
                    employment_rate=0.5,
                )
            )
            db_session.commit()
    return schools


def _count_queries(db_session, func):
    """统计 func 执行期间发生的 SQL 查询次数"""
    query_count = 0

    @event.listens_for(db_session.bind, "before_cursor_execute")
    def _counter(*args, **kwargs):
        nonlocal query_count
        query_count += 1

    try:
        result = func()
    finally:
        event.remove(db_session.bind, "before_cursor_execute", _counter)
    return result, query_count


# ----------------------------------------------------------------------
# 修复 B4: list_schools N+1 查询
# ----------------------------------------------------------------------
class TestListSchoolsPerformance:
    def test_list_schools_no_n_plus_1_query(self, db_session):
        """list_schools 应使用单条 GROUP BY 聚合，避免 N+1（2N+1）"""
        _seed_multi_schools(db_session)  # 3 所学校

        result, query_count = _count_queries(db_session, lambda: list_schools(db_session))

        # 3 所学校 -> N+1 模式下为 1 + 3*2 = 7 次查询；聚合后应 <= 2
        assert query_count <= 2, (
            f"list_schools 执行了 {query_count} 次查询，疑似 N+1（期望单条聚合 <=2）"
        )
        assert len(result) == 2  # 只有清华、北大有已发布报告

    def test_list_schools_aggregation_correctness(self, db_session):
        """聚合查询后的 report_count 与 major_count 应正确"""
        _seed_multi_schools(db_session)
        result = list_schools(db_session)
        by_name = {r["name"]: r for r in result}
        assert "清华大学" in by_name
        assert "北京大学" in by_name
        assert "复旦大学" not in by_name  # 无已发布报告
        assert by_name["清华大学"]["report_count"] == 2
        assert by_name["清华大学"]["major_count"] == 1
        assert by_name["北京大学"]["report_count"] == 2
        assert by_name["北京大学"]["major_count"] == 1


# ----------------------------------------------------------------------
# 修复 B5: get_stats 全表载入内存
# ----------------------------------------------------------------------
class TestGetStatsPerformance:
    def test_get_stats_uses_aggregate_not_full_load(self, db_session):
        """get_stats 访问 report_records 的 SQL 应使用聚合函数，而非 SELECT 全表"""
        _seed_multi_schools(db_session)

        statements = []

        @event.listens_for(db_session.bind, "before_cursor_execute")
        def _capture(conn, cursor, statement, params, context, executemany):
            statements.append(statement)

        try:
            get_stats(db_session)
        finally:
            event.remove(db_session.bind, "before_cursor_execute", _capture)

        # 任何访问 report_records 的 SELECT 都必须包含聚合函数
        for stmt in statements:
            lower = stmt.lower()
            if "report_records" in lower and lower.lstrip().startswith("select"):
                has_agg = any(fn in lower for fn in ("count(", "min(", "max("))
                assert has_agg, (
                    f"get_stats 存在全表载入查询（缺少聚合函数）: {stmt}"
                )

    def test_get_stats_empty_db(self, db_session):
        """空数据库时 year_range 应为 [None, None]，不应因 min/max 空序列报错"""
        stats = get_stats(db_session)
        assert stats["school_count"] == 0
        assert stats["report_count"] == 0
        assert stats["major_count"] == 0
        assert stats["year_range"] == [None, None]

    def test_get_stats_multi_school_correctness(self, db_session):
        """多学校场景下 COUNT(DISTINCT) 统计应正确"""
        _seed_multi_schools(db_session)
        stats = get_stats(db_session)
        assert stats["school_count"] == 2  # 清华 + 北大（DISTINCT school_id）
        assert stats["report_count"] == 4  # 2 校 * 2 年
        assert stats["major_count"] == 2   # 专业1 + 专业2（DISTINCT major）
        assert stats["year_range"] == [2023, 2024]


# ----------------------------------------------------------------------
# 修复: ilike 未转义 LIKE 通配符
# ----------------------------------------------------------------------
class TestEscapeLike:
    def test_escape_like_percent(self):
        from app.services.employment_service import escape_like
        assert escape_like("100%") == "100\\%"

    def test_escape_like_underscore(self):
        from app.services.employment_service import escape_like
        assert escape_like("a_b") == "a\\_b"

    def test_escape_like_normal_string(self):
        from app.services.employment_service import escape_like
        assert escape_like("清华") == "清华"

    def test_search_employment_escapes_percent(self, client, db_session):
        """搜索串中的 % 不应被当作 LIKE 通配符"""
        _seed_employment_data(db_session)  # 清华大学，名称不含 %
        # %25 是 % 的 URL 编码；若未转义，"%%%" 会匹配任意字符串
        resp = client.get("/api/employment/search?school=%25&major=机械")
        data = resp.json()
        assert data["school"] is None
        assert data["records"] == []

    def test_search_employment_escapes_underscore(self, client, db_session):
        """搜索串中的 _ 不应被当作单字符通配符"""
        _seed_employment_data(db_session)  # 清华大学，名称不含 _
        # 若未转义，"%_%" 会匹配任意长度>=1 的字符串
        resp = client.get("/api/employment/search?school=_&major=机械")
        data = resp.json()
        assert data["school"] is None

    def test_list_majors_escapes_wildcard(self, db_session):
        """list_majors 中的 LIKE 通配符应被转义"""
        _seed_employment_data(db_session)  # 清华大学
        assert list_majors(db_session, "%") == []
        assert list_majors(db_session, "_") == []


# ----------------------------------------------------------------------
# 修复: API 未声明 response_model
# ----------------------------------------------------------------------
class TestResponseModel:
    def test_all_endpoints_declare_response_model(self):
        """所有 employment 端点均应声明 response_model"""
        from app.api.employment import router
        missing = [
            route.path for route in router.routes if route.response_model is None
        ]
        assert not missing, f"以下端点未声明 response_model: {missing}"


# ----------------------------------------------------------------------
# 修复: SearchBody 定义位置错误
# ----------------------------------------------------------------------
class TestSearchBodyLocation:
    def test_search_body_defined_in_schemas(self):
        """SearchBody 应定义在 app.schemas.employment，而非 api 路由文件"""
        from app.api.employment import SearchBody
        assert SearchBody.__module__ == "app.schemas.employment"

    def test_search_body_importable_from_schemas(self):
        """SearchBody 应能从 app.schemas.employment 直接导入"""
        from app.schemas.employment import SearchBody
        body = SearchBody(school="清华", major="机械")
        assert body.school == "清华"
        assert body.major == "机械"
        assert body.year is None
        assert body.degree is None
