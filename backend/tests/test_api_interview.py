# backend/tests/test_api_interview.py
"""公司面试经验报告 API 测试。"""
import pytest


# ======================================================================
# 辅助函数
# ======================================================================

def _submit_report(client, headers, **overrides):
    """通过 API 提交一条面试报告，返回响应。"""
    payload = {
        "company": "腾讯",
        "position": "后端开发",
        "interview_year": 2024,
        "city": "深圳",
        "rounds": 3,
        "result": "offer",
        "dimensions": ["algorithm", "system_design"],
        "difficulty": 4,
        "summary": "侧重算法和系统设计",
    }
    payload.update(overrides)
    return client.post("/api/interview/submit", headers=headers, json=payload)


# ======================================================================
# 提交报告
# ======================================================================

class TestSubmitReport:
    def test_submit_report(self, auth_headers, client):
        """提交报告成功。"""
        resp = _submit_report(client, auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["company"] == "腾讯"
        assert data["position"] == "后端开发"
        assert data["interview_year"] == 2024
        assert data["result"] == "offer"
        assert data["dimensions"] == ["algorithm", "system_design"]
        assert data["difficulty"] == 4
        assert "id" in data

    def test_submit_report_minimal(self, auth_headers, client):
        """仅填写必填字段也可提交。"""
        resp = client.post(
            "/api/interview/submit",
            headers=auth_headers,
            json={
                "company": "字节跳动",
                "position": "前端开发",
                "interview_year": 2024,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["city"] is None
        assert data["rounds"] is None
        assert data["result"] == "pending"
        assert data["dimensions"] == []
        assert data["difficulty"] is None


class TestSubmitDuplicateUpsert:
    def test_submit_duplicate_upsert(self, auth_headers, client):
        """同一用户同公司同岗位同年重复提交应更新已有记录。"""
        resp1 = _submit_report(client, auth_headers, result="offer")
        assert resp1.status_code == 200
        report_id = resp1.json()["id"]

        resp2 = _submit_report(client, auth_headers, result="rejected")
        assert resp2.status_code == 200
        assert resp2.json()["id"] == report_id
        assert resp2.json()["result"] == "rejected"

        resp3 = client.get("/api/interview/my-reports", headers=auth_headers)
        assert resp3.status_code == 200
        assert len(resp3.json()) == 1


class TestMyReports:
    def test_my_reports(self, auth_headers, client):
        """查看自己的报告列表。"""
        for year in [2022, 2023, 2024]:
            _submit_report(client, auth_headers, interview_year=year)

        resp = client.get("/api/interview/my-reports", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 3
        years = [r["interview_year"] for r in data]
        assert years == [2024, 2023, 2022]

    def test_my_reports_empty(self, auth_headers, client):
        """无报告时返回空列表。"""
        resp = client.get("/api/interview/my-reports", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []


class TestDeleteReport:
    def test_delete_report(self, auth_headers, client):
        """删除自己的报告。"""
        resp = _submit_report(client, auth_headers)
        report_id = resp.json()["id"]

        resp_del = client.delete(
            f"/api/interview/{report_id}", headers=auth_headers
        )
        assert resp_del.status_code == 204

        resp_list = client.get("/api/interview/my-reports", headers=auth_headers)
        assert len(resp_list.json()) == 0

    def test_delete_nonexistent_report(self, auth_headers, client):
        """删除不存在的报告返回 404。"""
        fake_id = "00000000-0000-0000-0000-000000000000"
        resp = client.delete(f"/api/interview/{fake_id}", headers=auth_headers)
        assert resp.status_code == 404


# ======================================================================
# 聚合统计
# ======================================================================

class TestAggregate:
    def test_aggregate_sufficient(self, auth_headers, client):
        """样本 >= 3 时返回完整分布数据。"""
        _submit_report(
            client, auth_headers, interview_year=2022,
            dimensions=["algorithm", "system_design"], difficulty=4, result="offer",
        )
        _submit_report(
            client, auth_headers, interview_year=2023,
            dimensions=["algorithm", "project_depth"], difficulty=3, result="rejected",
        )
        _submit_report(
            client, auth_headers, interview_year=2024,
            dimensions=["algorithm", "system_design", "communication"], difficulty=5, result="offer",
        )

        resp = client.post(
            "/api/interview/aggregate",
            json={"company": "腾讯"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["sample_count"] == 3
        assert data["sufficient"] is True

        # 维度频率
        dims = data["dimension_frequency"]
        assert dims is not None
        assert pytest.approx(dims["algorithm"], rel=1e-2) == 1.0
        assert pytest.approx(dims["system_design"], rel=1e-2) == 2 / 3

        # 结果分布
        results = data["result_distribution"]
        assert results is not None
        assert pytest.approx(results["offer"], rel=1e-2) == 2 / 3
        assert pytest.approx(results["rejected"], rel=1e-2) == 1 / 3

        # 平均难度
        assert data["avg_difficulty"] == 4.0

    def test_aggregate_insufficient(self, auth_headers, client):
        """样本 < 3 时仅返回 sample_count，不返回分布数据。"""
        _submit_report(client, auth_headers, interview_year=2024)
        _submit_report(client, auth_headers, interview_year=2023)

        resp = client.post(
            "/api/interview/aggregate",
            json={"company": "腾讯"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["sample_count"] == 2
        assert data["sufficient"] is False
        assert data["dimension_frequency"] is None
        assert data["result_distribution"] is None

    def test_aggregate_zero_samples(self, client):
        """无匹配数据时 sample_count=0。"""
        resp = client.post(
            "/api/interview/aggregate",
            json={"company": "不存在的公司"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["sample_count"] == 0
        assert data["sufficient"] is False

    def test_aggregate_fuzzy_match(self, auth_headers, client):
        """ILIKE 模糊匹配。"""
        for year in [2022, 2023, 2024]:
            _submit_report(client, auth_headers, interview_year=year)

        resp = client.post(
            "/api/interview/aggregate",
            json={"company": "腾"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["sample_count"] == 3

    def test_aggregate_with_position_filter(self, auth_headers, client):
        """岗位过滤。"""
        _submit_report(client, auth_headers, interview_year=2022, position="后端开发")
        _submit_report(client, auth_headers, interview_year=2023, position="前端开发")
        _submit_report(client, auth_headers, interview_year=2024, position="后端开发")

        resp = client.post(
            "/api/interview/aggregate",
            json={"company": "腾讯", "position": "后端"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["sample_count"] == 2

    def test_aggregate_common_positions(self, auth_headers, client):
        """不指定岗位时返回常见岗位列表。"""
        _submit_report(client, auth_headers, interview_year=2022, position="后端开发")
        _submit_report(client, auth_headers, interview_year=2023, position="前端开发")
        _submit_report(client, auth_headers, interview_year=2024, position="后端开发")

        resp = client.post(
            "/api/interview/aggregate",
            json={"company": "腾讯"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["common_positions"] is not None
        assert len(data["common_positions"]) == 2


# ======================================================================
# 全局统计
# ======================================================================

class TestStats:
    def test_stats(self, auth_headers, client):
        """全局统计。"""
        _submit_report(client, auth_headers, company="腾讯", position="后端开发")
        _submit_report(client, auth_headers, company="腾讯", position="前端开发", interview_year=2023)
        _submit_report(client, auth_headers, company="字节跳动", position="后端开发", interview_year=2022)

        resp = client.get("/api/interview/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_reports"] == 3
        assert data["company_count"] == 2
        assert data["position_count"] == 2

    def test_stats_empty(self, client):
        """空数据库时统计为 0。"""
        resp = client.get("/api/interview/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_reports"] == 0


# ======================================================================
# 公司列表
# ======================================================================

class TestCompanies:
    def test_companies(self, auth_headers, client):
        """公司列表。"""
        _submit_report(client, auth_headers, company="腾讯", position="后端开发")
        _submit_report(client, auth_headers, company="腾讯", position="前端开发", interview_year=2023)
        _submit_report(client, auth_headers, company="字节跳动", position="后端开发", interview_year=2022)

        resp = client.post(
            "/api/interview/companies",
            json={"keyword": ""},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["name"] == "腾讯"
        assert data[0]["count"] == 2

    def test_companies_search(self, auth_headers, client):
        """模糊搜索公司。"""
        _submit_report(client, auth_headers, company="腾讯科技")
        _submit_report(client, auth_headers, company="字节跳动")

        resp = client.post(
            "/api/interview/companies",
            json={"keyword": "腾"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["name"] == "腾讯科技"


# ======================================================================
# 权限控制
# ======================================================================

class TestAuth:
    def test_anonymous_submit_fails(self, client):
        """未登录不能提交报告。"""
        resp = client.post(
            "/api/interview/submit",
            json={"company": "腾讯", "position": "后端开发", "interview_year": 2024},
        )
        assert resp.status_code == 401

    def test_anonymous_my_reports_fails(self, client):
        """未登录不能查看自己的报告。"""
        resp = client.get("/api/interview/my-reports")
        assert resp.status_code == 401

    def test_anonymous_delete_fails(self, client):
        """未登录不能删除报告。"""
        resp = client.delete("/api/interview/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 401

    def test_aggregate_no_auth_required(self, client):
        """聚合查询不需要登录。"""
        resp = client.post(
            "/api/interview/aggregate",
            json={"company": "腾讯"},
        )
        assert resp.status_code == 200

    def test_stats_no_auth_required(self, client):
        """全局统计不需要登录。"""
        resp = client.get("/api/interview/stats")
        assert resp.status_code == 200
