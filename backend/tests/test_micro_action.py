# backend/tests/test_micro_action.py
"""7天微行动 API 测试 — 创建计划 / 完成任务 / 跳过任务 / 进度 / 自我发现报告。"""

from collections import Counter


# ----------------------------------------------------------------------
# 辅助函数
# ----------------------------------------------------------------------
def _create_plan(client, auth_headers, path: str = "kaoyan", role: str | None = None):
    """创建一个 7 天计划，返回响应 JSON。"""
    payload = {"target_path": path}
    if role:
        payload["target_role"] = role
    resp = client.post(
        "/api/micro-actions/plans",
        headers=auth_headers,
        json=payload,
    )
    assert resp.status_code == 201, f"创建计划失败: {resp.text}"
    return resp.json()


def _get_first_task_id(plan: dict) -> str:
    return plan["tasks"][0]["id"]


# ----------------------------------------------------------------------
# 认证要求
# ----------------------------------------------------------------------
class TestAuthRequired:
    def test_create_plan_requires_auth(self, client):
        resp = client.post("/api/micro-actions/plans", json={"target_path": "kaoyan"})
        assert resp.status_code == 401

    def test_get_current_plan_requires_auth(self, client):
        resp = client.get("/api/micro-actions/plans/current")
        assert resp.status_code == 401

    def test_get_history_requires_auth(self, client):
        resp = client.get("/api/micro-actions/history")
        assert resp.status_code == 401

    def test_complete_task_requires_auth(self, client):
        resp = client.post(
            "/api/micro-actions/tasks/some-id/complete",
            json={"user_response": "x"},
        )
        assert resp.status_code == 401

    def test_skip_task_requires_auth(self, client):
        resp = client.post("/api/micro-actions/tasks/some-id/skip")
        assert resp.status_code == 401


# ----------------------------------------------------------------------
# 创建计划 / 生成 7 个任务
# ----------------------------------------------------------------------
class TestCreatePlan:
    def test_creates_seven_tasks(self, auth_headers, client):
        """创建计划后应生成 7 个任务。"""
        plan = _create_plan(client, auth_headers, path="kaoyan")
        assert plan["id"]
        assert plan["target_path"] == "kaoyan"
        assert plan["status"] == "active"
        assert len(plan["tasks"]) == 7
        # day_number 应为 1-7
        days = sorted(t["day_number"] for t in plan["tasks"])
        assert days == [1, 2, 3, 4, 5, 6, 7]
        # progress 初始应为 0
        assert plan["progress"] == 0

    def test_task_types_distribution(self, auth_headers, client):
        """7 个任务的类型分布：2 research + 1 interview + 2 practice + 2 reflect。"""
        plan = _create_plan(client, auth_headers, path="kaoyan")
        types = Counter(t["task_type"] for t in plan["tasks"])
        assert types["research"] == 2
        assert types["interview"] == 1
        assert types["practice"] == 2
        assert types["reflect"] == 2

    def test_all_tasks_pending_on_creation(self, auth_headers, client):
        plan = _create_plan(client, auth_headers)
        for t in plan["tasks"]:
            assert t["status"] == "pending"
            assert t["completed_at"] is None
            assert t["user_response"] is None
            assert t["insight"] is None

    def test_target_role_optional(self, auth_headers, client):
        plan = _create_plan(client, auth_headers, role="后端开发")
        assert plan["target_role"] == "后端开发"

    def test_unknown_path_falls_back_to_employment(self, auth_headers, client):
        """未知路径应兜底为 employment（生成 7 个任务）。"""
        plan = _create_plan(client, auth_headers, path="unknown_xyz")
        assert plan["target_path"] == "unknown_xyz"
        assert len(plan["tasks"]) == 7

    def test_each_path_generates_seven_tasks(self, auth_headers, client):
        """3 条路径都应生成 7 个任务。"""
        for path in ("kaoyan", "employment", "civil_service"):
            # 已有 active plan 会被废弃，可继续创建
            plan = _create_plan(client, auth_headers, path=path)
            assert len(plan["tasks"]) == 7


# ----------------------------------------------------------------------
# 完成任务
# ----------------------------------------------------------------------
class TestCompleteTask:
    def test_complete_marks_status(self, auth_headers, client):
        plan = _create_plan(client, auth_headers)
        task_id = _get_first_task_id(plan)

        resp = client.post(
            f"/api/micro-actions/tasks/{task_id}/complete",
            headers=auth_headers,
            json={"user_response": "今天查了3所院校，发现报录比远低于想象"},
        )
        assert resp.status_code == 200, resp.text
        task = resp.json()
        assert task["status"] == "completed"
        assert task["user_response"].startswith("今天查了3所")
        assert task["completed_at"] is not None
        # insight 应被生成（即使没 LLM key 也走模板兜底）
        assert task["insight"] is not None
        assert len(task["insight"]) > 0

    def test_complete_increases_progress(self, auth_headers, client):
        plan = _create_plan(client, auth_headers)
        task_id = _get_first_task_id(plan)

        client.post(
            f"/api/micro-actions/tasks/{task_id}/complete",
            headers=auth_headers,
            json={"user_response": "完成第一个任务"},
        )

        # 重新获取 current plan 应反映新的 progress
        resp = client.get("/api/micro-actions/plans/current", headers=auth_headers)
        assert resp.status_code == 200
        updated = resp.json()
        # 完成 1 / 7 ≈ 14%
        assert updated["progress"] == 14

    def test_complete_completes_plan_after_seven(self, auth_headers, client):
        """完成所有 7 个任务后 plan.status 应变为 completed。"""
        plan = _create_plan(client, auth_headers)
        for task in plan["tasks"]:
            resp = client.post(
                f"/api/micro-actions/tasks/{task['id']}/complete",
                headers=auth_headers,
                json={"user_response": f"第 {task['day_number']} 天的记录"},
            )
            assert resp.status_code == 200, resp.text

        # plan 状态应已更新（按 ID 查询，因为 /current 只返回 active plan）
        resp = client.get(
            f"/api/micro-actions/plans/{plan['id']}",
            headers=auth_headers,
        )
        updated = resp.json()
        assert updated["status"] == "completed"
        assert updated["progress"] == 100

    def test_complete_nonexistent_task_returns_404(self, auth_headers, client):
        resp = client.post(
            "/api/micro-actions/tasks/00000000-0000-0000-0000-000000000000/complete",
            headers=auth_headers,
            json={"user_response": "x"},
        )
        assert resp.status_code == 404

    def test_complete_invalid_uuid_returns_400(self, auth_headers, client):
        resp = client.post(
            "/api/micro-actions/tasks/not-a-uuid/complete",
            headers=auth_headers,
            json={"user_response": "x"},
        )
        assert resp.status_code == 400

    def test_complete_empty_response_rejected(self, auth_headers, client):
        plan = _create_plan(client, auth_headers)
        task_id = _get_first_task_id(plan)
        resp = client.post(
            f"/api/micro-actions/tasks/{task_id}/complete",
            headers=auth_headers,
            json={"user_response": ""},
        )
        assert resp.status_code == 422


# ----------------------------------------------------------------------
# 跳过任务
# ----------------------------------------------------------------------
class TestSkipTask:
    def test_skip_marks_status(self, auth_headers, client):
        plan = _create_plan(client, auth_headers)
        task_id = _get_first_task_id(plan)

        resp = client.post(
            f"/api/micro-actions/tasks/{task_id}/skip",
            headers=auth_headers,
        )
        assert resp.status_code == 200, resp.text
        task = resp.json()
        assert task["status"] == "skipped"
        assert task["completed_at"] is not None
        # 跳过不需要 user_response
        assert task["user_response"] is None

    def test_skip_counts_as_done_in_progress(self, auth_headers, client):
        """跳过也算「已处理」，progress 应增加。"""
        plan = _create_plan(client, auth_headers)
        task_id = _get_first_task_id(plan)

        client.post(f"/api/micro-actions/tasks/{task_id}/skip", headers=auth_headers)

        resp = client.get("/api/micro-actions/plans/current", headers=auth_headers)
        updated = resp.json()
        assert updated["progress"] == 14  # 1/7

    def test_skip_completes_plan_after_seven(self, auth_headers, client):
        """全部跳过也能让 plan 状态变为 completed。"""
        plan = _create_plan(client, auth_headers)
        for task in plan["tasks"]:
            resp = client.post(
                f"/api/micro-actions/tasks/{task['id']}/skip",
                headers=auth_headers,
            )
            assert resp.status_code == 200

        # 按 ID 查询，因为 /current 只返回 active plan
        resp = client.get(
            f"/api/micro-actions/plans/{plan['id']}",
            headers=auth_headers,
        )
        updated = resp.json()
        assert updated["status"] == "completed"
        assert updated["progress"] == 100


# ----------------------------------------------------------------------
# 获取计划 / 历史
# ----------------------------------------------------------------------
class TestGetPlans:
    def test_get_current_plan_none_when_empty(self, auth_headers, client):
        resp = client.get("/api/micro-actions/plans/current", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() is None

    def test_get_current_plan_after_create(self, auth_headers, client):
        plan = _create_plan(client, auth_headers)
        resp = client.get("/api/micro-actions/plans/current", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == plan["id"]
        assert len(body["tasks"]) == 7

    def test_get_specific_plan(self, auth_headers, client):
        plan = _create_plan(client, auth_headers)
        resp = client.get(
            f"/api/micro-actions/plans/{plan['id']}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == plan["id"]

    def test_get_nonexistent_plan_returns_404(self, auth_headers, client):
        resp = client.get(
            "/api/micro-actions/plans/00000000-0000-0000-0000-000000000000",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_history_empty(self, auth_headers, client):
        resp = client.get("/api/micro-actions/history", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_history_after_create(self, auth_headers, client):
        _create_plan(client, auth_headers, path="kaoyan")
        _create_plan(client, auth_headers, path="employment")

        resp = client.get("/api/micro-actions/history", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 2
        # 倒序：最新在前
        assert body[0]["target_path"] == "employment"
        assert body[1]["target_path"] == "kaoyan"
        # 第一个被废弃，第二个 active
        assert body[1]["status"] == "abandoned"
        assert body[0]["status"] == "active"

    def test_creating_new_plan_abandons_old_active(self, auth_headers, client):
        """创建新 plan 时应把旧 active plan 标记为 abandoned。"""
        first = _create_plan(client, auth_headers, path="kaoyan")
        assert first["status"] == "active"

        second = _create_plan(client, auth_headers, path="employment")
        assert second["status"] == "active"

        # 旧的 plan 现在应为 abandoned
        resp = client.get(
            f"/api/micro-actions/plans/{first['id']}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "abandoned"

        # current plan 应为第二个
        resp = client.get("/api/micro-actions/plans/current", headers=auth_headers)
        assert resp.json()["id"] == second["id"]


# ----------------------------------------------------------------------
# 进度计算
# ----------------------------------------------------------------------
class TestProgressCalculation:
    def test_progress_zero_at_start(self, auth_headers, client):
        plan = _create_plan(client, auth_headers)
        assert plan["progress"] == 0

    def test_progress_partial(self, auth_headers, client):
        plan = _create_plan(client, auth_headers)
        # 完成 3 个任务 → 3/7 ≈ 42%
        for task in plan["tasks"][:3]:
            client.post(
                f"/api/micro-actions/tasks/{task['id']}/complete",
                headers=auth_headers,
                json={"user_response": "记录"},
            )
        resp = client.get("/api/micro-actions/plans/current", headers=auth_headers)
        assert resp.json()["progress"] == 42

    def test_progress_full_after_all_done(self, auth_headers, client):
        plan = _create_plan(client, auth_headers)
        # 混合完成 + 跳过
        for i, task in enumerate(plan["tasks"]):
            if i % 2 == 0:
                client.post(
                    f"/api/micro-actions/tasks/{task['id']}/complete",
                    headers=auth_headers,
                    json={"user_response": "x"},
                )
            else:
                client.post(
                    f"/api/micro-actions/tasks/{task['id']}/skip",
                    headers=auth_headers,
                )
        # 按 ID 查询（plan 已完成，不再是 active）
        resp = client.get(
            f"/api/micro-actions/plans/{plan['id']}",
            headers=auth_headers,
        )
        body = resp.json()
        assert body["progress"] == 100
        assert body["status"] == "completed"


# ----------------------------------------------------------------------
# 自我发现报告
# ----------------------------------------------------------------------
class TestSelfDiscoveryReport:
    def test_report_generated_on_completion(self, auth_headers, client, db_session):
        """完成所有 7 个任务后，plan.self_discovery_report 应非空。

        实际生成由 generate_self_discovery_report 触发，
        本测试通过完成所有任务后检查 plan 是否进入 completed，
        并通过显式调用 service.generate_self_discovery_report 验证模板兜底路径。
        """
        import asyncio

        from uuid import UUID

        from app.services import micro_action_service as svc

        plan = _create_plan(client, auth_headers)
        plan_id = plan["id"]

        for task in plan["tasks"]:
            client.post(
                f"/api/micro-actions/tasks/{task['id']}/complete",
                headers=auth_headers,
                json={"user_response": f"第 {task['day_number']} 天：发现了一些细节"},
            )

        # 检查 plan 完成状态（按 ID 查询，因为 /current 只返回 active plan）
        resp = client.get(
            f"/api/micro-actions/plans/{plan_id}",
            headers=auth_headers,
        )
        body = resp.json()
        assert body["status"] == "completed"

        # 显式调用 service 生成报告（测试无 LLM key 时的模板兜底）
        # 直接使用 db_session fixture（client 与 service 共享同一个 SQLite session）
        report = asyncio.run(svc.generate_self_discovery_report(db_session, UUID(plan_id)))
        assert report
        assert "自我发现" in report or "喜好" in report
        # 报告应包含三段式结构关键字
        assert "喜好" in report
        assert "挑战" in report
        assert "下一步" in report

        # 重新拉取 plan 应能看到 self_discovery_report 已写入
        resp = client.get(f"/api/micro-actions/plans/{plan_id}", headers=auth_headers)
        body = resp.json()
        assert body["self_discovery_report"]
        assert "喜好" in body["self_discovery_report"]
