# backend/tests/test_review_center.py
"""复盘中心 API 测试 — 认证 / CRUD / action_refs 转换 / 轨迹联动 / AI 模板降级。"""

from tests.test_action_center import _checkin, _create_action


def _create_review(client, auth_headers, idempotency=None, **overrides):
    headers = dict(auth_headers)
    if idempotency:
        headers["X-Idempotency-Key"] = idempotency
    payload = {
        "review_type": "weekly",
        "period_start": "2026-08-03",
        "period_end": "2026-08-09",
        "content": "本周完成了模拟面试练习，发现表达仍不够结构化。",
        "action_refs": [1, 2],
        "mood_score": 4,
        **overrides,
    }
    return client.post("/api/v1/reviews", headers=headers, json=payload)


# ----------------------------------------------------------------------
# 认证要求
# ----------------------------------------------------------------------
class TestAuthRequired:
    def test_create_requires_auth(self, client):
        resp = client.post(
            "/api/v1/reviews",
            json={
                "review_type": "weekly",
                "period_start": "2026-08-03",
                "period_end": "2026-08-09",
                "content": "x",
            },
        )
        assert resp.status_code == 401

    def test_list_requires_auth(self, client):
        assert client.get("/api/v1/reviews").status_code == 401

    def test_detail_requires_auth(self, client):
        assert client.get("/api/v1/reviews/1").status_code == 401

    def test_ai_analyze_requires_auth(self, client):
        resp = client.post("/api/v1/reviews/1/ai-analyze", json={"review_id": 1})
        assert resp.status_code == 401


# ----------------------------------------------------------------------
# 创建复盘
# ----------------------------------------------------------------------
class TestCreateReview:
    def test_create_ok(self, auth_headers, client):
        resp = _create_review(client, auth_headers)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["id"]
        assert body["user_id"]  # UUID 已注入
        assert body["review_type"] == "weekly"
        assert body["content"].startswith("本周完成了模拟面试练习")
        assert body["status"] == "DRAFT"
        assert body["mood_score"] == 4

    def test_action_refs_converted_to_dict(self, auth_headers, client):
        """action_refs: list 落库转换为 {"action_ids": [...]} dict。"""
        body = _create_review(client, auth_headers).json()
        assert body["action_refs"] == {"action_ids": [1, 2]}

    def test_idempotency_key_returns_same_review(self, auth_headers, client):
        first = _create_review(client, auth_headers, idempotency="review-001").json()
        second = _create_review(client, auth_headers, idempotency="review-001").json()
        assert first["id"] == second["id"]

    def test_create_writes_growth_trajectory(self, auth_headers, client):
        """创建复盘联动写入成长轨迹（event_type=review_completed）。"""
        _create_review(client, auth_headers, idempotency="review-traj")
        items = client.get("/api/v1/growth/trajectory", headers=auth_headers).json()["items"]
        assert len(items) == 1
        assert items[0]["event_type"] == "review_completed"
        assert items[0]["event_payload"]["review_type"] == "weekly"
        assert items[0]["source_event_id"] == "review-traj"

    def test_invalid_mood_score_rejected(self, auth_headers, client):
        resp = _create_review(client, auth_headers, mood_score=9)
        assert resp.status_code == 422


# ----------------------------------------------------------------------
# 详情 / 列表
# ----------------------------------------------------------------------
class TestReadReview:
    def test_detail(self, auth_headers, client):
        review = _create_review(client, auth_headers).json()
        resp = client.get(f"/api/v1/reviews/{review['id']}", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == review["id"]
        assert body["ai_summary"] is None  # 未分析前为 None

    def test_detail_nonexistent_404(self, auth_headers, client):
        assert client.get("/api/v1/reviews/999999", headers=auth_headers).status_code == 404

    def test_user_isolation(self, auth_headers, client):
        """其他用户的复盘不可读。"""
        review = _create_review(client, auth_headers).json()
        client.post(
            "/api/auth/register",
            json={"email": "other2@example.com", "password": "Test1234!", "name": "其他"},
        )
        resp2 = client.post(
            "/api/auth/login",
            json={"email": "other2@example.com", "password": "Test1234!"},
        )
        other_headers = {"Authorization": f"Bearer {resp2.json()['access_token']}"}
        assert client.get(
            f"/api/v1/reviews/{review['id']}", headers=other_headers
        ).status_code == 404

    def test_list_paginated(self, auth_headers, client):
        for i in range(3):
            _create_review(client, auth_headers, idempotency=f"list-{i}")
        resp = client.get("/api/v1/reviews?page=1&size=2", headers=auth_headers)
        body = resp.json()
        assert body["total"] == 3
        assert len(body["items"]) == 2


# ----------------------------------------------------------------------
# AI 复盘分析（模板降级）
# ----------------------------------------------------------------------
class TestAiAnalyze:
    def _analyze(self, client, auth_headers, review_id, **overrides):
        payload = {"review_id": review_id, **overrides}
        return client.post(
            f"/api/v1/reviews/{review_id}/ai-analyze",
            headers=auth_headers,
            json=payload,
        )

    def test_template_fallback(self, auth_headers, client, monkeypatch):
        """LLM 不可用（未配置）→ 模板降级，仍写回并 status=COMPLETED。"""
        from app.services.ai_service import AIServiceNotConfigured
        from app.services import review_service

        class _StubOrchestrator:
            def chat(self, *args, **kwargs):
                raise AIServiceNotConfigured("LLM_API_KEY 未配置")

        monkeypatch.setattr(review_service, "AIOrchestrator", lambda: _StubOrchestrator())

        review = _create_review(client, auth_headers).json()
        resp = self._analyze(client, auth_headers, review["id"], focus_areas=["总结"])
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["status"] == "COMPLETED"
        assert body["summary"]  # 模板摘要非空
        assert isinstance(body["insights"], list)
        assert isinstance(body["suggestions"], list)
        assert 0.0 <= body["uncertainty_score"] <= 1.0
        assert body["created_at"]  # 契约 created_at 已映射

    def test_ai_result_endpoint(self, auth_headers, client, monkeypatch):
        from app.services.ai_service import AIServiceNotConfigured
        from app.services import review_service

        class _StubOrchestrator:
            def chat(self, *args, **kwargs):
                raise AIServiceNotConfigured("no key")

        monkeypatch.setattr(review_service, "AIOrchestrator", lambda: _StubOrchestrator())

        review = _create_review(client, auth_headers).json()
        self._analyze(client, auth_headers, review["id"])
        resp = client.get(f"/api/v1/reviews/{review['id']}/ai-result", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["review_id"] == review["id"]
        assert body["status"] == "COMPLETED"

    def test_reanalyze_returns_existing(self, auth_headers, client, monkeypatch):
        """已 COMPLETED 的复盘重复触发 AI 分析 → 直接返回既有结果（幂等）。"""
        calls = {"n": 0}
        from app.services.ai_service import AIServiceNotConfigured
        from app.services import review_service

        class _StubOrchestrator:
            def chat(self, *args, **kwargs):
                calls["n"] += 1
                raise AIServiceNotConfigured("no key")

        monkeypatch.setattr(review_service, "AIOrchestrator", lambda: _StubOrchestrator())

        review = _create_review(client, auth_headers).json()
        self._analyze(client, auth_headers, review["id"])
        self._analyze(client, auth_headers, review["id"])
        assert calls["n"] == 1  # 第二次未重新调用 LLM

    def test_analyze_nonexistent_404(self, auth_headers, client):
        resp = self._analyze(client, auth_headers, 999999)
        assert resp.status_code == 404


# ----------------------------------------------------------------------
# 复盘与行动联动（可选演示路径）
# ----------------------------------------------------------------------
class TestReviewActionLinking:
    def test_checkin_and_review_flow(self, auth_headers, client):
        """行动打卡 + 复盘创建 → 轨迹含两类事件。"""
        action = _create_action(client, auth_headers)
        _checkin(client, auth_headers, action["id"], idempotency="flow-checkin")
        _create_review(client, auth_headers, idempotency="flow-review")

        items = client.get("/api/v1/growth/trajectory", headers=auth_headers).json()["items"]
        event_types = sorted(i["event_type"] for i in items)
        assert event_types == ["action_checkin", "review_completed"]

        # 复盘可关联真实行动 ID（先建行动再复盘）
        review = _create_review(
            client, auth_headers, idempotency="flow-review-2",
            period_start="2026-08-10", period_end="2026-08-12",
            action_refs=[action["id"]],
        ).json()
        assert review["action_refs"] == {"action_ids": [action["id"]]}
        assert review["period_start"] == "2026-08-10"
