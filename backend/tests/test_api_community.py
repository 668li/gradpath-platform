"""社区数据 API 测试。"""
import pytest


class TestCommunitySubmit:
    def test_submit_report_success(self, client, auth_headers):
        """提交社区报告成功"""
        resp = client.post(
            "/api/community/submit",
            headers=auth_headers,
            json={
                "school_name": "清华大学",
                "major": "计算机科学",
                "graduation_year": 2024,
                "destination_type": "employment",
                "employer": "字节跳动",
                "salary_range": "15k_25k",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["school_name"] == "清华大学"
        assert data["major"] == "计算机科学"

    def test_submit_report_unauthorized(self, client):
        """未登录提交报告应返回401"""
        resp = client.post(
            "/api/community/submit",
            json={
                "school_name": "清华大学",
                "major": "计算机科学",
                "graduation_year": 2024,
                "destination_type": "employment",
                "employer": "字节跳动",
                "salary_range": "15k_25k",
            },
        )
        assert resp.status_code in [401, 403]

    def test_submit_report_invalid_data(self, client, auth_headers):
        """提交无效数据应返回422"""
        resp = client.post(
            "/api/community/submit",
            headers=auth_headers,
            json={},
        )
        assert resp.status_code == 422


class TestCommunityMyReports:
    def test_list_my_reports(self, client, auth_headers):
        """获取我的报告列表"""
        # 先提交一条报告
        client.post(
            "/api/community/submit",
            headers=auth_headers,
            json={
                "school_name": "北京大学",
                "major": "软件工程",
                "graduation_year": 2024,
                "destination_type": "further_study",
                "employer": "北京大学",
                "salary_range": "prefer_not",
            },
        )

        resp = client.get("/api/community/my-reports", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data

    def test_list_my_reports_unauthorized(self, client):
        """未登录获取报告列表应返回401"""
        resp = client.get("/api/community/my-reports")
        assert resp.status_code in [401, 403]


class TestCommunityDelete:
    def test_delete_report_success(self, client, auth_headers):
        """删除报告成功"""
        # 先提交一条报告
        submit_resp = client.post(
            "/api/community/submit",
            headers=auth_headers,
            json={
                "school_name": "浙江大学",
                "major": "人工智能",
                "graduation_year": 2024,
                "destination_type": "employment",
                "employer": "阿里巴巴",
                "salary_range": "25k_50k",
            },
        )
        report_id = submit_resp.json()["id"]

        resp = client.delete(f"/api/community/{report_id}", headers=auth_headers)
        assert resp.status_code == 204

    def test_delete_report_not_found(self, client, auth_headers):
        """删除不存在的报告应返回404"""
        resp = client.delete(
            "/api/community/00000000-0000-0000-0000-000000000000",
            headers=auth_headers,
        )
        assert resp.status_code == 404


class TestCommunityAggregate:
    def test_aggregate_endpoint(self, client):
        """聚合查询接口"""
        resp = client.post(
            "/api/community/aggregate",
            json={
                "school": "清华大学",
                "major": "计算机科学",
                "year": 2024,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "sample_count" in data


class TestCommunityStats:
    def test_stats_endpoint(self, client):
        """社区统计接口"""
        resp = client.get("/api/community/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_reports" in data or "total" in data
