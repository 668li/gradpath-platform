# backend/tests/test_pagination.py
"""分页接口测试 — 验证 5 个列表端点的分页响应结构。"""
from datetime import date, timedelta


# ======================================================================
# 辅助构造函数
# ======================================================================

def _create_decision(client, headers, decision_date: str):
    """通过 API 创建一条去向决策，返回响应 JSON。"""
    resp = client.post(
        "/api/decisions",
        headers=headers,
        json={
            "decision_date": decision_date,
            "destination_type": "employment",
            "status": "planned",
            "details": {},
            "reasoning": "...",
            "confidence": 3,
        },
    )
    assert resp.status_code == 201
    return resp.json()


def _create_event(client, headers, event_date: str, title: str):
    """通过 API 创建一条职业事件，返回响应 JSON。"""
    resp = client.post(
        "/api/events",
        headers=headers,
        json={
            "event_date": event_date,
            "event_type": "other",
            "title": title,
            "description": "...",
        },
    )
    assert resp.status_code == 201
    return resp.json()


def _create_retrospective(client, headers, period_end: str, title: str):
    """通过 API 创建一条复盘，返回响应 JSON。"""
    resp = client.post(
        "/api/retrospectives",
        headers=headers,
        json={
            "period_type": "quarterly",
            "period_start": "2025-01-01",
            "period_end": period_end,
            "title": title,
            "achievements": [],
            "challenges": "...",
            "lessons_learned": "...",
            "next_steps": [],
            "satisfaction": 3,
        },
    )
    assert resp.status_code == 201
    return resp.json()


def _create_interview_report(client, headers, company: str, position: str, year: int):
    """通过 API 创建一条面试报告，返回响应 JSON。"""
    resp = client.post(
        "/api/interview/submit",
        headers=headers,
        json={
            "company": company,
            "position": position,
            "interview_year": year,
        },
    )
    assert resp.status_code == 200
    return resp.json()


# ======================================================================
# 去向决策
# ======================================================================

class TestDecisionPagination:
    def test_decision_first_page(self, auth_headers, client):
        """创建 5 条决策，page=1&page_size=2 返回 2 条，total=5。"""
        base = date(2026, 1, 1)
        for i in range(5):
            d = (base + timedelta(days=i)).isoformat()
            _create_decision(client, auth_headers, d)

        resp = client.get(
            "/api/decisions?page=1&page_size=2", headers=auth_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 2
        assert data["total"] == 5
        assert data["page"] == 1
        assert data["page_size"] == 2

    def test_decision_second_page_different_items(self, auth_headers, client):
        """page=2 返回与 page=1 不同的记录。"""
        base = date(2026, 1, 1)
        for i in range(5):
            d = (base + timedelta(days=i)).isoformat()
            _create_decision(client, auth_headers, d)

        page1 = client.get(
            "/api/decisions?page=1&page_size=2", headers=auth_headers
        ).json()
        page2 = client.get(
            "/api/decisions?page=2&page_size=2", headers=auth_headers
        ).json()

        assert len(page2["items"]) == 2
        assert page2["total"] == 5
        ids1 = {item["id"] for item in page1["items"]}
        ids2 = {item["id"] for item in page2["items"]}
        # 两页记录互不相同
        assert ids1.isdisjoint(ids2)


# ======================================================================
# 职业事件
# ======================================================================

class TestEventPagination:
    def test_event_total_count(self, auth_headers, client):
        """创建 3 条事件，page=1&page_size=10 返回全部 3 条，total=3。"""
        base = date(2026, 3, 1)
        for i in range(3):
            d = (base + timedelta(days=i)).isoformat()
            _create_event(client, auth_headers, d, f"事件-{i}")

        resp = client.get(
            "/api/events?page=1&page_size=10", headers=auth_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 3
        assert data["total"] == 3
        assert data["page"] == 1
        assert data["page_size"] == 10

    def test_event_second_page(self, auth_headers, client):
        """page=2&page_size=2 返回 1 条（3 条中第 1 页占 2 条）。"""
        base = date(2026, 3, 1)
        for i in range(3):
            d = (base + timedelta(days=i)).isoformat()
            _create_event(client, auth_headers, d, f"事件-{i}")

        resp = client.get(
            "/api/events?page=2&page_size=2", headers=auth_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 1
        assert data["total"] == 3


# ======================================================================
# 阶段复盘
# ======================================================================

class TestRetrospectivePagination:
    def test_retrospective_pagination(self, auth_headers, client):
        """创建 5 条复盘，分页返回正确。"""
        base = date(2025, 3, 31)
        for i in range(5):
            d = (base + timedelta(days=i)).isoformat()
            _create_retrospective(client, auth_headers, d, f"复盘-{i}")

        # 第 1 页 2 条
        page1 = client.get(
            "/api/retrospectives?page=1&page_size=2", headers=auth_headers
        ).json()
        assert len(page1["items"]) == 2
        assert page1["total"] == 5
        assert page1["page"] == 1
        assert page1["page_size"] == 2

        # 第 3 页 1 条（5 条：2 + 2 + 1）
        page3 = client.get(
            "/api/retrospectives?page=3&page_size=2", headers=auth_headers
        ).json()
        assert len(page3["items"]) == 1
        assert page3["total"] == 5


# ======================================================================
# 社区数据
# ======================================================================

class TestCommunityPagination:
    def test_community_empty(self, auth_headers, client):
        """无数据时 total=0、items 为空列表。"""
        resp = client.get(
            "/api/community/my-reports?page=1&page_size=20", headers=auth_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["items"] == []
        assert data["page"] == 1
        assert data["page_size"] == 20


# ======================================================================
# 面试经验
# ======================================================================

class TestInterviewPagination:
    def test_interview_total_count(self, auth_headers, client):
        """创建 2 条面试报告，total=2。"""
        _create_interview_report(client, auth_headers, "腾讯", "后端开发", 2024)
        _create_interview_report(
            client, auth_headers, "字节跳动", "前端开发", 2023
        )

        resp = client.get(
            "/api/interview/my-reports?page=1&page_size=20", headers=auth_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 2
        assert data["total"] == 2
        assert data["page"] == 1
        assert data["page_size"] == 20


# ======================================================================
# page_size 边界
# ======================================================================

class TestPageSizeBoundary:
    def test_page_size_boundary(self, auth_headers, client):
        """page_size=100 通过校验返回 200，page_size=101 超出上限返回 422。"""
        _create_decision(client, auth_headers, "2026-01-01")

        # 上限值 100 应通过
        resp_ok = client.get(
            "/api/decisions?page=1&page_size=100", headers=auth_headers
        )
        assert resp_ok.status_code == 200
        assert resp_ok.json()["page_size"] == 100

        # 超出上限 101 应被拒绝
        resp_over = client.get(
            "/api/decisions?page=1&page_size=101", headers=auth_headers
        )
        assert resp_over.status_code == 422
