# backend/tests/test_path_conflict.py
"""路径冲突调解 API 测试 — detect / resolve / history / detail。"""


# ----------------------------------------------------------------------
# 辅助：构造测评/决策数据
# ----------------------------------------------------------------------
def _submit_assessment(client, auth_headers, answers: dict):
    """提交一次测评，返回响应 JSON。"""
    resp = client.post(
        "/api/assessment/submit",
        headers=auth_headers,
        json={"answers": answers},
    )
    assert resp.status_code == 201, f"测评提交失败: {resp.text}"
    return resp.json()


def _create_decision(client, auth_headers, destination_type: str = "civil_service"):
    """创建一条去向决策，返回响应 JSON。"""
    resp = client.post(
        "/api/decisions",
        headers=auth_headers,
        json={
            "decision_date": "2026-07-15",
            "destination_type": destination_type,
            "status": "planned",
            "details": {},
            "reasoning": "已选定方向",
            "confidence": 4,
        },
    )
    assert resp.status_code == 201, f"决策创建失败: {resp.text}"
    return resp.json()


# Holland RIA 答案 — 推荐技术/研究类方向（与考公冲突）
_RIA_ANSWERS = {
    "q1": "R",
    "q2": "I",
    "q3": "A",
    "q4": "R",
    "q5": "I",
    "q6": "A",
    "q7": "R",
    "q8": "I",
    "q9": "A",
    "q10": "R",
    "q11": "I",
    "q12": "A",
}


# ----------------------------------------------------------------------
# detect 端点
# ----------------------------------------------------------------------
class TestDetectConflict:
    def test_detect_requires_auth(self, client):
        """detect 端点必须带 token。"""
        resp = client.post("/api/path-conflict/detect")
        assert resp.status_code == 401

    def test_detect_no_assessment(self, auth_headers, client):
        """无测评数据时返回 has_conflict=False。"""
        resp = client.post("/api/path-conflict/detect", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["has_conflict"] is False
        assert data["conflict_type"] == "no_assessment"
        assert data["assessment_summary"] == {}
        assert data["options"] == []
        assert "测评" in data["message"]

    def test_detect_no_decision(self, auth_headers, client):
        """有测评但无决策时返回 has_conflict=False。"""
        _submit_assessment(client, auth_headers, _RIA_ANSWERS)
        resp = client.post("/api/path-conflict/detect", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["has_conflict"] is False
        assert data["conflict_type"] == "no_decision"
        assert data["assessment_summary"] != {}
        assert data["current_situation"] == {}

    def test_detect_with_conflict(self, auth_headers, client):
        """测评推荐技术方向 + 当前考公 → 应检测到冲突并返回 3 条选项。"""
        _submit_assessment(client, auth_headers, _RIA_ANSWERS)
        _create_decision(client, auth_headers, destination_type="civil_service")

        resp = client.post("/api/path-conflict/detect", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["has_conflict"] is True
        assert data["conflict_type"] == "assessment_vs_current"
        assert data["conflict_id"]  # 非空，用于后续 resolve
        assert len(data["options"]) == 3

        # 校验 3 条选项结构
        for i, opt in enumerate(data["options"]):
            assert opt["id"] == i
            assert opt["title"]
            assert opt["description"]
            assert isinstance(opt["pros"], list)
            assert isinstance(opt["cons"], list)
            assert opt["risk_level"] in ("low", "medium", "high")

    def test_detect_no_conflict_same_track(self, auth_headers, client):
        """测评推荐就业方向 + 当前就业决策 → 不应检测到冲突。"""
        _submit_assessment(client, auth_headers, _RIA_ANSWERS)
        _create_decision(client, auth_headers, destination_type="employment")

        resp = client.post("/api/path-conflict/detect", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["has_conflict"] is False


# ----------------------------------------------------------------------
# resolve 端点
# ----------------------------------------------------------------------
class TestResolveConflict:
    def test_resolve_requires_auth(self, client):
        resp = client.post(
            "/api/path-conflict/resolve",
            json={"conflict_id": "abc", "selected_option": 0, "reasoning": ""},
        )
        assert resp.status_code == 401

    def test_resolve_invalid_conflict_id(self, auth_headers, client):
        """非法 conflict_id 返回 400。"""
        resp = client.post(
            "/api/path-conflict/resolve",
            headers=auth_headers,
            json={"conflict_id": "not-a-uuid", "selected_option": 0, "reasoning": ""},
        )
        assert resp.status_code == 400

    def test_resolve_not_found(self, auth_headers, client):
        """不存在的 conflict_id 返回 404。"""
        resp = client.post(
            "/api/path-conflict/resolve",
            headers=auth_headers,
            json={
                "conflict_id": "00000000-0000-0000-0000-000000000000",
                "selected_option": 0,
                "reasoning": "",
            },
        )
        assert resp.status_code == 404

    def test_resolve_success(self, auth_headers, client):
        """完整流程：detect → resolve，应生成行动计划。"""
        _submit_assessment(client, auth_headers, _RIA_ANSWERS)
        _create_decision(client, auth_headers, destination_type="civil_service")

        detect_resp = client.post("/api/path-conflict/detect", headers=auth_headers)
        conflict_id = detect_resp.json()["conflict_id"]

        resp = client.post(
            "/api/path-conflict/resolve",
            headers=auth_headers,
            json={
                "conflict_id": conflict_id,
                "selected_option": 2,  # 折中方案
                "reasoning": "想保留考公机会同时发展技术副业",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["selected_option"] == 2
        assert data["reasoning"] == "想保留考公机会同时发展技术副业"
        # 行动计划应非空
        assert isinstance(data["action_plan"], dict)
        assert data["action_plan"].get("summary")
        assert isinstance(data["action_plan"].get("milestones"), list)
        assert len(data["action_plan"]["milestones"]) > 0

    def test_resolve_invalid_selected_option(self, auth_headers, client):
        """selected_option 超出 0-2 范围返回 422。"""
        _submit_assessment(client, auth_headers, _RIA_ANSWERS)
        _create_decision(client, auth_headers, destination_type="civil_service")
        detect_resp = client.post("/api/path-conflict/detect", headers=auth_headers)
        conflict_id = detect_resp.json()["conflict_id"]

        resp = client.post(
            "/api/path-conflict/resolve",
            headers=auth_headers,
            json={"conflict_id": conflict_id, "selected_option": 5, "reasoning": ""},
        )
        assert resp.status_code == 422


# ----------------------------------------------------------------------
# history / detail 端点
# ----------------------------------------------------------------------
class TestHistoryAndDetail:
    def test_history_requires_auth(self, client):
        resp = client.get("/api/path-conflict/history")
        assert resp.status_code == 401

    def test_history_empty(self, auth_headers, client):
        """无历史记录时返回空列表。"""
        resp = client.get("/api/path-conflict/history", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_history_after_resolve(self, auth_headers, client):
        """完成一次 resolve 后，history 应包含该记录。"""
        _submit_assessment(client, auth_headers, _RIA_ANSWERS)
        _create_decision(client, auth_headers, destination_type="civil_service")
        detect_resp = client.post("/api/path-conflict/detect", headers=auth_headers)
        conflict_id = detect_resp.json()["conflict_id"]
        client.post(
            "/api/path-conflict/resolve",
            headers=auth_headers,
            json={"conflict_id": conflict_id, "selected_option": 0, "reasoning": "test"},
        )

        resp = client.get("/api/path-conflict/history", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert data[0]["selected_option"] == 0

    def test_detail_requires_auth(self, client):
        resp = client.get("/api/path-conflict/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 401

    def test_detail_not_found(self, auth_headers, client):
        resp = client.get(
            "/api/path-conflict/00000000-0000-0000-0000-000000000000",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_detail_success(self, auth_headers, client):
        """获取单条记录详情。"""
        _submit_assessment(client, auth_headers, _RIA_ANSWERS)
        _create_decision(client, auth_headers, destination_type="civil_service")
        detect_resp = client.post("/api/path-conflict/detect", headers=auth_headers)
        conflict_id = detect_resp.json()["conflict_id"]
        client.post(
            "/api/path-conflict/resolve",
            headers=auth_headers,
            json={"conflict_id": conflict_id, "selected_option": 1, "reasoning": "转向"},
        )

        resp = client.get(f"/api/path-conflict/{conflict_id}", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == conflict_id
        assert data["selected_option"] == 1
        assert data["reasoning"] == "转向"


# ----------------------------------------------------------------------
# 服务层单元测试（不依赖 HTTP）
# ----------------------------------------------------------------------
class TestServiceLayer:
    def test_generate_options_returns_three(self, db_session, auth_headers, client):
        """generate_options 模板生成器应返回 3 条选项。"""
        from app.services.path_conflict_service import generate_options

        assessment = {
            "type": "holland",
            "result_code": "RIA",
            "directions": ["后端开发", "数据分析师"],
        }
        situation = {
            "destination_type": "civil_service",
            "destination_type_label": "考公",
            "status": "planned",
        }
        options = generate_options(assessment, situation)
        assert len(options) == 3
        titles = [o["title"] for o in options]
        assert "坚持现状" in titles
        assert "转向推荐" in titles
        assert "折中方案" in titles

        # 校验每条结构
        for opt in options:
            assert "description" in opt
            assert "pros" in opt and isinstance(opt["pros"], list)
            assert "cons" in opt and isinstance(opt["cons"], list)
            assert "estimated_timeline" in opt
            assert opt["risk_level"] in ("low", "medium", "high")

    def test_generate_action_plan_per_option(self, db_session):
        """generate_action_plan 应为 0/1/2 分别生成不同计划。"""
        from app.services.path_conflict_service import _generate_action_plan_template

        for selected in (0, 1, 2):
            plan = _generate_action_plan_template(selected, "测试", "后端开发", "考公")
            assert plan["summary"], f"selected={selected} 缺少 summary"
            assert isinstance(plan["milestones"], list) and len(plan["milestones"]) > 0
            assert isinstance(plan["resources"], list)
            assert isinstance(plan["risks"], list)
