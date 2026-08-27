# backend/tests/test_family_dialogue.py
"""家庭对话脚手架 API 测试 — start / session / practice / history。"""

import pytest


# ----------------------------------------------------------------------
# start 端点
# ----------------------------------------------------------------------
class TestStartSession:
    def test_start_requires_auth(self, client):
        """start 端点必须带 token。"""
        resp = client.post(
            "/api/family-dialogue/start",
            json={
                "parent_concern": "爸妈想让我考公",
                "user_choice": "我想去互联网公司",
                "parent_archetype": "stability_first",
            },
        )
        assert resp.status_code == 401

    def test_start_invalid_archetype(self, auth_headers, client):
        """非法 parent_archetype 返回 400。"""
        resp = client.post(
            "/api/family-dialogue/start",
            headers=auth_headers,
            json={
                "parent_concern": "爸妈想让我考公",
                "user_choice": "我想去互联网公司",
                "parent_archetype": "unknown_type",
            },
        )
        assert resp.status_code == 400

    def test_start_missing_fields(self, auth_headers, client):
        """缺少必填字段返回 422。"""
        resp = client.post(
            "/api/family-dialogue/start",
            headers=auth_headers,
            json={"parent_concern": "考公", "user_choice": "互联网"},
        )
        assert resp.status_code == 422

    def test_start_success(self, auth_headers, client):
        """成功启动会话，返回理解分析 + 论据 + 沟通技巧。"""
        resp = client.post(
            "/api/family-dialogue/start",
            headers=auth_headers,
            json={
                "parent_concern": "爸妈想让我考公务员",
                "user_choice": "我想去互联网大厂做开发",
                "parent_archetype": "stability_first",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"]
        assert data["parent_concern"] == "爸妈想让我考公务员"
        assert data["user_choice"] == "我想去互联网大厂做开发"
        assert data["parent_archetype"] == "stability_first"
        assert data["status"] == "preparing"
        # 理解分析非空
        assert data["understanding"]
        # 论据 3-5 条
        assert 3 <= len(data["arguments"]) <= 5
        # 沟通技巧非空
        assert len(data["talking_tips"]) > 0
        # 模拟对话记录初始为空
        assert data["practice_messages"] == []

    @pytest.mark.parametrize(
        "archetype",
        ["stability_first", "prestige_first", "practical_worry", "supportive"],
    )
    def test_start_all_archetypes_generate_arguments(self, auth_headers, client, archetype):
        """4 种父母类型都能生成 arguments。"""
        resp = client.post(
            "/api/family-dialogue/start",
            headers=auth_headers,
            json={
                "parent_concern": "爸妈想让我考公",
                "user_choice": "我想去互联网公司",
                "parent_archetype": archetype,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["arguments"]) >= 3
        assert data["understanding"]


# ----------------------------------------------------------------------
# arguments 结构校验
# ----------------------------------------------------------------------
class TestArgumentStructure:
    def test_arguments_have_four_fields(self, auth_headers, client):
        """每条 argument 含 4 个字段：parent_saying/user_response/data_backing/empathy_note。"""
        resp = client.post(
            "/api/family-dialogue/start",
            headers=auth_headers,
            json={
                "parent_concern": "爸妈想让我考公",
                "user_choice": "我想去互联网大厂",
                "parent_archetype": "practical_worry",
            },
        )
        assert resp.status_code == 200
        args = resp.json()["arguments"]
        assert len(args) >= 3
        for arg in args:
            assert "parent_saying" in arg and arg["parent_saying"]
            assert "user_response" in arg and arg["user_response"]
            assert "data_backing" in arg and arg["data_backing"]
            assert "empathy_note" in arg and arg["empathy_note"]

    def test_arguments_for_different_scenarios(self, auth_headers, client):
        """不同用户选择（不同场景）都能生成 arguments。"""
        cases = [
            ("爸妈想让我考公", "我想去互联网公司做开发"),
            ("爸妈想让我直接就业", "我想考研读研深造"),
            ("爸妈想让我国内读研", "我想出国留学"),
            ("爸妈想让我稳定就业", "我想创业"),
            ("爸妈想让我考公", "我是文科生想转行互联网"),
        ]
        for concern, choice in cases:
            resp = client.post(
                "/api/family-dialogue/start",
                headers=auth_headers,
                json={
                    "parent_concern": concern,
                    "user_choice": choice,
                    "parent_archetype": "stability_first",
                },
            )
            assert resp.status_code == 200, f"场景失败: {choice} -> {resp.text}"
            args = resp.json()["arguments"]
            assert len(args) >= 3


# ----------------------------------------------------------------------
# session 详情端点
# ----------------------------------------------------------------------
class TestGetSession:
    def test_get_requires_auth(self, client):
        resp = client.get("/api/family-dialogue/session/abc")
        assert resp.status_code == 401

    def test_get_not_found(self, auth_headers, client):
        resp = client.get(
            "/api/family-dialogue/session/00000000-0000-0000-0000-000000000000",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_get_success(self, auth_headers, client):
        """启动后能通过 id 取回会话详情。"""
        start = client.post(
            "/api/family-dialogue/start",
            headers=auth_headers,
            json={
                "parent_concern": "爸妈想让我考公",
                "user_choice": "我想去互联网公司",
                "parent_archetype": "stability_first",
            },
        )
        sid = start.json()["id"]

        resp = client.get(f"/api/family-dialogue/session/{sid}", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == sid
        assert data["parent_concern"] == "爸妈想让我考公"


# ----------------------------------------------------------------------
# practice 模拟对话端点
# ----------------------------------------------------------------------
class TestPractice:
    def test_practice_requires_auth(self, client):
        resp = client.post(
            "/api/family-dialogue/session/00000000-0000-0000-0000-000000000000/practice",
            json={"message": "爸妈我想去互联网"},
        )
        assert resp.status_code == 401

    def test_practice_session_not_found(self, auth_headers, client):
        resp = client.post(
            "/api/family-dialogue/session/00000000-0000-0000-0000-000000000000/practice",
            headers=auth_headers,
            json={"message": "爸妈我想去互联网"},
        )
        assert resp.status_code == 404

    def test_practice_success(self, auth_headers, client):
        """模拟对话练习：用户输入后返回 parent role 回复。"""
        start = client.post(
            "/api/family-dialogue/start",
            headers=auth_headers,
            json={
                "parent_concern": "爸妈想让我考公",
                "user_choice": "我想去互联网公司",
                "parent_archetype": "stability_first",
            },
        )
        sid = start.json()["id"]

        resp = client.post(
            f"/api/family-dialogue/session/{sid}/practice",
            headers=auth_headers,
            json={"message": "爸妈，互联网薪资高，我想先去试试"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["role"] == "parent"
        assert data["content"]

    def test_practice_multiple_rounds(self, auth_headers, client):
        """多轮对话：每次返回不同回复，对话记录累积。"""
        start = client.post(
            "/api/family-dialogue/start",
            headers=auth_headers,
            json={
                "parent_concern": "爸妈想让我考公",
                "user_choice": "我想去互联网公司",
                "parent_archetype": "prestige_first",
            },
        )
        sid = start.json()["id"]

        messages = [
            "爸妈，互联网薪资高，我想先去试试",
            "可是考公更稳定啊",
            "我会给自己设止损线，3 年不行就回来考公",
        ]
        replies = []
        for msg in messages:
            resp = client.post(
                f"/api/family-dialogue/session/{sid}/practice",
                headers=auth_headers,
                json={"message": msg},
            )
            assert resp.status_code == 200
            replies.append(resp.json())

        # 至少有一条回复与其它不同（轮换模板）
        contents = [r["content"] for r in replies]
        assert len(set(contents)) >= 2

        # 会话状态变为 practiced
        detail = client.get(f"/api/family-dialogue/session/{sid}", headers=auth_headers).json()
        assert detail["status"] == "practiced"
        # 对话记录应包含 user + parent 各 3 条 = 6 条
        assert len(detail["practice_messages"]) == 6


# ----------------------------------------------------------------------
# history 端点
# ----------------------------------------------------------------------
class TestHistory:
    def test_history_requires_auth(self, client):
        resp = client.get("/api/family-dialogue/history")
        assert resp.status_code == 401

    def test_history_empty(self, auth_headers, client):
        """无历史记录时返回空列表。"""
        resp = client.get("/api/family-dialogue/history", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_history_after_start(self, auth_headers, client):
        """启动会话后，history 应包含该记录。"""
        client.post(
            "/api/family-dialogue/start",
            headers=auth_headers,
            json={
                "parent_concern": "考公",
                "user_choice": "互联网",
                "parent_archetype": "supportive",
            },
        )
        resp = client.get("/api/family-dialogue/history", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert data[0]["parent_archetype"] == "supportive"


# ----------------------------------------------------------------------
# 服务层单元测试（不依赖 HTTP）
# ----------------------------------------------------------------------
class TestServiceLayer:
    def test_detect_scenario(self, db_session):
        """场景识别器应正确匹配关键词。"""
        from app.services.family_dialogue_service import _detect_scenario

        assert _detect_scenario("我想去互联网大厂", "考公") == "internet_vs_civil"
        assert _detect_scenario("我想考研", "") == "kaoyan_vs_employment"
        assert _detect_scenario("想出国留学", "") == "abroad_vs_domestic"
        assert _detect_scenario("我想创业", "") == "startup_vs_employment"
        assert _detect_scenario("文科转行", "") == "liberal_arts_transition"

    def test_scenario_arguments_count(self, db_session):
        """每个预设场景至少有 3 条 argument 模板。"""
        from app.services.family_dialogue_service import _SCENARIO_ARGUMENTS

        for scenario, args in _SCENARIO_ARGUMENTS.items():
            assert len(args) >= 3, f"场景 {scenario} 论据不足 3 条"

    def test_all_archetypes_have_replies(self, db_session):
        """4 种父母类型都有预设回复模板。"""
        from app.services.family_dialogue_service import _PRACTICE_REPLIES, PARENT_ARCHETYPE_LABELS

        for archetype in PARENT_ARCHETYPE_LABELS:
            assert archetype in _PRACTICE_REPLIES
            assert len(_PRACTICE_REPLIES[archetype]) >= 3
