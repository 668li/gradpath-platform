# backend/tests/test_assessment.py
"""职业测评 API 测试 — 霍兰德职业兴趣测评。"""


# 一组覆盖 R/I/A/S 四个维度的完整答案（每维度 3 次）
_SAMPLE_ANSWERS = {
    "q1": "R", "q2": "I", "q3": "A", "q4": "R",
    "q5": "S", "q6": "A", "q7": "R", "q8": "I",
    "q9": "S", "q10": "I", "q11": "A", "q12": "S",
}


class TestAssessmentQuestions:
    def test_get_questions_no_auth(self, client):
        """获取题目列表无需认证，返回 48 题（霍兰德扩展题库）。"""
        resp = client.get("/api/assessment/questions")
        assert resp.status_code == 200
        questions = resp.json()
        assert len(questions) == 48
        q = questions[0]
        assert set(q.keys()) == {"id", "question", "options"}
        assert len(q["options"]) == 2
        assert set(q["options"][0].keys()) == {"value", "label"}

    def test_get_questions_returns_all_dimensions(self, client):
        """题目选项覆盖霍兰德 6 个维度。"""
        resp = client.get("/api/assessment/questions")
        values = {
            opt["value"]
            for q in resp.json()
            for opt in q["options"]
        }
        assert values == {"R", "I", "A", "S", "E", "C"}


class TestAssessmentSubmit:
    def test_submit_returns_result(self, auth_headers, client):
        """提交答案返回计算结果，result_code 与推荐方向非空。"""
        resp = client.post(
            "/api/assessment/submit",
            headers=auth_headers,
            json={"answers": _SAMPLE_ANSWERS},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["assessment_type"] == "holland"
        assert data["result_code"]  # 非空
        assert data["result_summary"]
        assert isinstance(data["recommended_directions"], list)
        assert len(data["recommended_directions"]) > 0
        assert isinstance(data["scores"], dict)
        assert len(data["scores"]) > 0
        assert data["id"]

    def test_submit_and_get_latest_result(self, auth_headers, client):
        """提交后可通过 /result 获取最近一次结果。"""
        resp = client.post(
            "/api/assessment/submit",
            headers=auth_headers,
            json={"answers": _SAMPLE_ANSWERS},
        )
        submitted_id = resp.json()["id"]

        resp2 = client.get("/api/assessment/result", headers=auth_headers)
        assert resp2.status_code == 200
        latest = resp2.json()
        assert latest["id"] == submitted_id
        assert latest["result_code"] == resp.json()["result_code"]
        assert latest["scores"] == resp.json()["scores"]

    def test_submit_unauthenticated_401(self, client):
        """未认证提交被拒绝。"""
        resp = client.post(
            "/api/assessment/submit",
            json={"answers": {"q1": "R"}},
        )
        assert resp.status_code == 401


class TestAssessmentHistory:
    def test_history_returns_all_records(self, auth_headers, client):
        """历史记录返回全部测评，按时间倒序。"""
        first = client.post(
            "/api/assessment/submit",
            headers=auth_headers,
            json={"answers": _SAMPLE_ANSWERS},
        ).json()
        second = client.post(
            "/api/assessment/submit",
            headers=auth_headers,
            json={"answers": _SAMPLE_ANSWERS},
        ).json()

        resp = client.get("/api/assessment/history", headers=auth_headers)
        assert resp.status_code == 200
        history = resp.json()
        assert len(history) == 2
        # 倒序：最新在前
        assert history[0]["id"] == second["id"]
        assert history[1]["id"] == first["id"]

    def test_result_empty_returns_null(self, auth_headers, client):
        """无测评记录时 /result 返回 null。"""
        resp = client.get("/api/assessment/result", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() is None

    def test_history_empty(self, auth_headers, client):
        """无测评记录时 /history 返回空列表。"""
        resp = client.get("/api/assessment/history", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_result_unauthenticated_401(self, client):
        """未认证访问 /result 被拒绝。"""
        resp = client.get("/api/assessment/result")
        assert resp.status_code == 401
