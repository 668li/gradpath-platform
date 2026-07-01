# backend/tests/test_api_community.py
"""社区毕业去向报告 API 测试。"""
import pytest


# ======================================================================
# 辅助函数
# ======================================================================

def _submit_report(client, headers, **overrides):
    """通过 API 提交一条社区报告，返回响应。"""
    payload = {
        "school_name": "清华大学",
        "major": "计算机科学与技术",
        "graduation_year": 2024,
        "degree": "bachelor",
        "destination_type": "employment",
        "employer": "字节跳动",
        "city": "北京",
        "industry": "互联网",
        "salary_range": "25k_50k",
    }
    payload.update(overrides)
    return client.post("/api/community/submit", headers=headers, json=payload)


# ======================================================================
# 提交报告
# ======================================================================

class TestSubmitReport:
    def test_submit_report(self, auth_headers, client):
        """提交报告成功。"""
        resp = _submit_report(client, auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["school_name"] == "清华大学"
        assert data["major"] == "计算机科学与技术"
        assert data["graduation_year"] == 2024
        assert data["destination_type"] == "employment"
        assert data["employer"] == "字节跳动"
        assert data["city"] == "北京"
        assert data["industry"] == "互联网"
        assert data["salary_range"] == "25k_50k"
        assert data["degree"] == "bachelor"
        assert "id" in data

    def test_submit_report_minimal(self, auth_headers, client):
        """仅填写必填字段也可提交。"""
        resp = client.post(
            "/api/community/submit",
            headers=auth_headers,
            json={
                "school_name": "北京大学",
                "major": "金融学",
                "graduation_year": 2024,
                "destination_type": "further_study",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["employer"] is None
        assert data["city"] is None
        assert data["industry"] is None
        assert data["salary_range"] is None
        assert data["degree"] == "bachelor"  # 默认值


class TestSubmitDuplicateUpsert:
    def test_submit_duplicate_upsert(self, auth_headers, client):
        """同一用户同年重复提交应更新已有记录（upsert）。"""
        # 第一次提交
        resp1 = _submit_report(client, auth_headers, employer="字节跳动")
        assert resp1.status_code == 200
        report_id = resp1.json()["id"]

        # 第二次提交（同年，不同 employer）—— 应更新而非新增
        resp2 = _submit_report(client, auth_headers, employer="腾讯")
        assert resp2.status_code == 200
        assert resp2.json()["id"] == report_id  # 同一条记录
        assert resp2.json()["employer"] == "腾讯"

        # my-reports 应只有 1 条
        resp3 = client.get("/api/community/my-reports", headers=auth_headers)
        assert resp3.status_code == 200
        items = resp3.json()["items"]
        assert len(items) == 1
        assert items[0]["employer"] == "腾讯"


class TestMyReports:
    def test_my_reports(self, auth_headers, client):
        """查看自己的报告列表。"""
        for year in [2022, 2023, 2024]:
            _submit_report(client, auth_headers, graduation_year=year)

        resp = client.get("/api/community/my-reports", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()["items"]
        assert len(data) == 3
        # 应按毕业年份降序排列
        years = [r["graduation_year"] for r in data]
        assert years == [2024, 2023, 2022]

    def test_my_reports_empty(self, auth_headers, client):
        """无报告时返回空列表。"""
        resp = client.get("/api/community/my-reports", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["items"] == []


class TestDeleteReport:
    def test_delete_report(self, auth_headers, client):
        """删除自己的报告。"""
        resp = _submit_report(client, auth_headers)
        report_id = resp.json()["id"]

        # 删除
        resp_del = client.delete(
            f"/api/community/{report_id}", headers=auth_headers
        )
        assert resp_del.status_code == 204

        # my-reports 应为空
        resp_list = client.get("/api/community/my-reports", headers=auth_headers)
        assert resp_list.status_code == 200
        assert len(resp_list.json()["items"]) == 0

    def test_delete_nonexistent_report(self, auth_headers, client):
        """删除不存在的报告返回 404。"""
        fake_id = "00000000-0000-0000-0000-000000000000"
        resp = client.delete(f"/api/community/{fake_id}", headers=auth_headers)
        assert resp.status_code == 404

    def test_delete_invalid_uuid(self, auth_headers, client):
        """无效 UUID 格式返回 404。"""
        resp = client.delete("/api/community/not-a-uuid", headers=auth_headers)
        assert resp.status_code == 404


# ======================================================================
# 聚合统计
# ======================================================================

class TestAggregate:
    def test_aggregate_sufficient(self, auth_headers, client):
        """样本 >= 3 时返回完整分布数据。"""
        # 3 条报告：2 条就业（字节跳动/北京/互联网/25k_50k），1 条升学
        _submit_report(
            client, auth_headers,
            graduation_year=2022, destination_type="employment",
            employer="字节跳动", city="北京", industry="互联网",
            salary_range="25k_50k",
        )
        _submit_report(
            client, auth_headers,
            graduation_year=2023, destination_type="employment",
            employer="字节跳动", city="北京", industry="互联网",
            salary_range="25k_50k",
        )
        _submit_report(
            client, auth_headers,
            graduation_year=2024, destination_type="further_study",
            employer=None, city=None, industry=None, salary_range=None,
        )

        resp = client.post(
            "/api/community/aggregate",
            json={"school": "清华大学", "major": "计算机科学与技术"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["sample_count"] == 3
        assert data["sufficient"] is True

        # 去向分布
        dist = data["destination_distribution"]
        assert dist is not None
        assert pytest.approx(dist["employment"], rel=1e-2) == 2 / 3
        assert pytest.approx(dist["further_study"], rel=1e-2) == 1 / 3

        # 热门雇主
        employers = data["top_employers"]
        assert employers is not None
        assert len(employers) >= 1
        assert employers[0]["name"] == "字节跳动"
        assert employers[0]["count"] == 2

        # 热门城市
        cities = data["top_cities"]
        assert cities is not None
        assert any(c["name"] == "北京" and c["count"] == 2 for c in cities)

        # 热门行业
        industries = data["top_industries"]
        assert industries is not None
        assert any(i["name"] == "互联网" and i["count"] == 2 for i in industries)

        # 薪资分布
        salaries = data["salary_distribution"]
        assert salaries is not None
        assert salaries.get("25k_50k") == 2

    def test_aggregate_insufficient(self, auth_headers, client):
        """样本 < 3 时仅返回 sample_count，不返回分布数据。"""
        _submit_report(
            client, auth_headers,
            graduation_year=2024, destination_type="employment",
            employer="腾讯", city="深圳",
        )
        _submit_report(
            client, auth_headers,
            graduation_year=2023, destination_type="employment",
            employer="阿里", city="杭州",
        )

        resp = client.post(
            "/api/community/aggregate",
            json={"school": "清华大学", "major": "计算机科学与技术"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["sample_count"] == 2
        assert data["sufficient"] is False
        assert data["destination_distribution"] is None
        assert data["top_employers"] is None
        assert data["top_cities"] is None
        assert data["top_industries"] is None
        assert data["salary_distribution"] is None

    def test_aggregate_zero_samples(self, client):
        """无匹配数据时 sample_count=0，sufficient=False。"""
        resp = client.post(
            "/api/community/aggregate",
            json={"school": "不存在的大学", "major": "不存在的专业"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["sample_count"] == 0
        assert data["sufficient"] is False

    def test_aggregate_fuzzy_match(self, auth_headers, client):
        """ILIKE 模糊匹配：用部分名称查询能匹配到完整名称。"""
        _submit_report(
            client, auth_headers,
            school_name="清华大学", major="计算机科学与技术",
            graduation_year=2024,
        )
        _submit_report(
            client, auth_headers,
            school_name="清华大学", major="计算机科学与技术",
            graduation_year=2023,
        )
        _submit_report(
            client, auth_headers,
            school_name="清华大学", major="计算机科学与技术",
            graduation_year=2022,
        )

        # 用 "清华" 模糊匹配 "清华大学"，用 "计算机" 模糊匹配 "计算机科学与技术"
        resp = client.post(
            "/api/community/aggregate",
            json={"school": "清华", "major": "计算机"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["sample_count"] == 3
        assert data["sufficient"] is True

    def test_aggregate_with_year_filter(self, auth_headers, client):
        """年份过滤：仅聚合指定年份的数据。"""
        for year in [2022, 2023, 2024]:
            _submit_report(
                client, auth_headers,
                school_name="测试大学", major="测试专业",
                graduation_year=year,
            )

        resp = client.post(
            "/api/community/aggregate",
            json={"school": "测试大学", "major": "测试专业", "year": 2024},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["sample_count"] == 1


# ======================================================================
# 全局统计
# ======================================================================

class TestStats:
    def test_stats(self, auth_headers, client):
        """全局统计：报告总数、学校数、专业数。"""
        _submit_report(
            client, auth_headers,
            school_name="清华大学", major="计算机科学与技术",
            graduation_year=2024,
        )
        _submit_report(
            client, auth_headers,
            school_name="清华大学", major="电子工程",
            graduation_year=2023,
        )
        _submit_report(
            client, auth_headers,
            school_name="北京大学", major="金融学",
            graduation_year=2022,
        )

        resp = client.get("/api/community/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_reports"] == 3
        assert data["school_count"] == 2  # 清华 + 北大
        assert data["major_count"] == 3   # 计算机 + 电子工程 + 金融学

    def test_stats_empty(self, client):
        """空数据库时统计为 0。"""
        resp = client.get("/api/community/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_reports"] == 0
        assert data["school_count"] == 0
        assert data["major_count"] == 0


# ======================================================================
# 权限控制
# ======================================================================

class TestAuth:
    def test_anonymous_submit_fails(self, client):
        """未登录不能提交报告。"""
        resp = client.post(
            "/api/community/submit",
            json={
                "school_name": "清华大学",
                "major": "计算机科学与技术",
                "graduation_year": 2024,
                "destination_type": "employment",
            },
        )
        assert resp.status_code == 401

    def test_anonymous_my_reports_fails(self, client):
        """未登录不能查看自己的报告。"""
        resp = client.get("/api/community/my-reports")
        assert resp.status_code == 401

    def test_anonymous_delete_fails(self, client):
        """未登录不能删除报告。"""
        resp = client.delete("/api/community/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 401

    def test_aggregate_no_auth_required(self, client):
        """聚合查询不需要登录。"""
        resp = client.post(
            "/api/community/aggregate",
            json={"school": "清华大学", "major": "计算机科学与技术"},
        )
        assert resp.status_code == 200

    def test_stats_no_auth_required(self, client):
        """全局统计不需要登录。"""
        resp = client.get("/api/community/stats")
        assert resp.status_code == 200
