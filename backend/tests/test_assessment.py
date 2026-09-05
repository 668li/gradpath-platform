# backend/tests/test_assessment.py
"""职业测评 API 测试 — 霍兰德职业兴趣测评。"""

# 一组覆盖 R/I/A/S 四个维度的完整答案（每维度 3 次）
_SAMPLE_ANSWERS = {
    "q1": "R",
    "q2": "I",
    "q3": "A",
    "q4": "R",
    "q5": "S",
    "q6": "A",
    "q7": "R",
    "q8": "I",
    "q9": "S",
    "q10": "I",
    "q11": "A",
    "q12": "S",
}


def _full_answers(prefix: str, values: list[str], count: int | None = None) -> dict:
    """生成覆盖某测评『全部题目』的合法答案（用于完整性校验通过的场景）。"""
    return {f"{prefix}_q{i}": values[i % len(values)] for i in range(1, (count or 48) + 1)}


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
        values = {opt["value"] for q in resp.json() for opt in q["options"]}
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


class TestAssessmentScoresSemantics:
    """B2：scores 必须是真实维度分，不是大五 Likert 选项计数。"""

    def test_big_five_scores_are_dimension_means(self, auth_headers, client):
        """大五 scores 为各维度均分 dict[str,float]（0-5），而非答案选项计数。"""
        answers = _full_answers("bf", ["3"], count=50)  # 全 3 分，每维均分应为 3.0
        resp = client.post(
            "/api/assessment/submit",
            headers=auth_headers,
            json={"answers": answers, "assessment_type": "big_five"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert set(data["scores"].keys()) == {"O", "C", "E", "A", "N"}
        for dim in ("O", "C", "E", "A", "N"):
            assert data["scores"][dim] == 3.0

    def test_holland_scores_count_dimensions(self, auth_headers, client):
        """霍兰德 scores 为维度计数的 int 值。"""
        answers = _full_answers("q", ["R", "I", "A"], count=48)
        resp = client.post(
            "/api/assessment/submit",
            headers=auth_headers,
            json={"answers": answers, "assessment_type": "holland"},
        )
        assert resp.status_code == 201
        data = resp.json()
        for code in ("R", "I", "A"):
            assert data["scores"].get(code, 0) == 16  # 48 题三选一轮转，各 16
        assert sum(data["scores"].values()) == 48


class TestAssessmentBigFiveShort:
    """Book 2：大五 10 题短版（big_five_short）——与 50 题版口径一致，摘要如实标注分辨率。"""

    def test_short_flat_answers_are_dimension_means(self, auth_headers, client):
        answers = _full_answers("bfs", ["3"], count=10)  # 全 3 分，每维均分应为 3.0
        resp = client.post(
            "/api/assessment/submit",
            headers=auth_headers,
            json={"answers": answers, "assessment_type": "big_five_short"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert set(data["scores"].keys()) == {"O", "C", "E", "A", "N"}
        for dim in ("O", "C", "E", "A", "N"):
            assert data["scores"][dim] == 3.0
        assert data["result_code"] == "O3C3E3A3N3"
        assert "短版" in data["result_summary"]  # 低分辨率如实标注

    def test_short_mixed_scores_and_directions(self, auth_headers, client):
        answers = {**_full_answers("bfs", ["5"], count=2)}  # O: 5,5
        answers.update({f"bfs_q{i}": "1" for i in (3, 4)})  # C: 1,1
        answers.update({f"bfs_q{i}": "3" for i in (5, 6)})  # E: 3,3
        answers.update({f"bfs_q{i}": "4" for i in (7, 8)})  # A: 4,4
        answers.update({f"bfs_q{i}": "2" for i in (9, 10)})  # N: 2,2
        resp = client.post(
            "/api/assessment/submit",
            headers=auth_headers,
            json={"answers": answers, "assessment_type": "big_five_short"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["scores"] == {"O": 5.0, "C": 1.0, "E": 3.0, "A": 4.0, "N": 2.0}
        assert data["result_code"] == "O5C1E3A4N2"
        assert data["recommended_directions"]  # top2 维度（O/A）有推荐方向

    def test_short_incomplete_appends_missing_warning(self, auth_headers, client):
        answers = _full_answers("bfs", ["3"], count=9)  # 少交 1 题
        resp = client.post(
            "/api/assessment/submit",
            headers=auth_headers,
            json={"answers": answers, "assessment_type": "big_five_short"},
        )
        assert resp.status_code == 201
        assert "缺失" in resp.json()["result_summary"]

    def test_short_single_option_warns(self, auth_headers, client):
        answers = _full_answers("bfs", ["4"], count=10)
        resp = client.post(
            "/api/assessment/submit",
            headers=auth_headers,
            json={"answers": answers, "assessment_type": "big_five_short"},
        )
        assert resp.status_code == 201
        assert "同一选项" in resp.json()["result_summary"]

    def test_short_low_variance_warns(self, auth_headers, client):
        """方差过低检查对短版生效：9×3 + 1×4 → 方差 0.09 < 0.3，但 unique=2
        不触发"同一选项"，只触发"区分度低"。"""
        answers = _full_answers("bfs", ["3"], count=10)
        answers["bfs_q5"] = "4"
        resp = client.post(
            "/api/assessment/submit",
            headers=auth_headers,
            json={"answers": answers, "assessment_type": "big_five_short"},
        )
        assert resp.status_code == 201
        summary = resp.json()["result_summary"]
        assert "区分度低" in summary
        assert "同一选项" not in summary


class TestAssessmentValidation:
    """B3：后端答案完整性 + 作答可信度校验。"""

    def test_incomplete_submit_appends_warning(self, auth_headers, client):
        """只交几题就提交 → result_summary 附带缺失警示，但仍返回结果。"""
        resp = client.post(
            "/api/assessment/submit",
            headers=auth_headers,
            json={"answers": {"q1": "R", "q2": "I"}},
        )
        assert resp.status_code == 201
        assert "作答提示" in resp.json()["result_summary"]
        assert "缺失" in resp.json()["result_summary"]

    def test_single_option_submit_warns_low_discernment(self, auth_headers, client):
        """全答同一选项 → 附作答模式单一警示（防乱答从后端拦截）。"""
        answers = {f"q{i}": "R" for i in range(1, 49)}  # 48 题全 R
        resp = client.post(
            "/api/assessment/submit",
            headers=auth_headers,
            json={"answers": answers, "assessment_type": "holland"},
        )
        assert resp.status_code == 201
        assert "同一选项" in resp.json()["result_summary"]

    def test_big_five_low_variance_warns(self, auth_headers, client):
        """大五作答集中在小区间 → 附区分度低警示。"""
        answers = _full_answers("bf", ["3"], count=50)
        resp = client.post(
            "/api/assessment/submit",
            headers=auth_headers,
            json={"answers": answers, "assessment_type": "big_five"},
        )
        assert resp.status_code == 201
        assert "区分度低" in resp.json()["result_summary"]

    def test_holland_flat_profile_warns_low_discernment(self, auth_headers, client):
        """霍兰德六维计数无区分度（第1−第4≤2）→ 附降级提示，引导看真实数据解读。"""
        values = ["R", "I", "A", "S", "E", "C"]
        answers = {f"q{i}": values[(i - 1) % 6] for i in range(1, 49)}  # 每维 8
        resp = client.post(
            "/api/assessment/submit",
            headers=auth_headers,
            json={"answers": answers, "assessment_type": "holland"},
        )
        assert resp.status_code == 201
        assert "区分度较低" in resp.json()["result_summary"]

    def test_holland_differentiated_profile_no_flat_warning(self, auth_headers, client):
        """维度分明显有偏向（第1−第4=8）→ 不附降级提示。"""
        seq = ["R"] * 14 + ["I"] * 10 + ["A"] * 8 + ["S"] * 6 + ["E"] * 5 + ["C"] * 5
        answers = {f"q{i}": seq[i - 1] for i in range(1, 49)}
        resp = client.post(
            "/api/assessment/submit",
            headers=auth_headers,
            json={"answers": answers, "assessment_type": "holland"},
        )
        assert resp.status_code == 201
        assert "区分度较低" not in resp.json()["result_summary"]


class TestAssessmentInterpret:
    """B1：测评 × 专有报考数据 → 专属路径解读。"""

    _post = "/api/assessment/interpret"

    def test_no_assessment_still_returns_paths_structure(self, auth_headers, client):
        """未完成测评（2026-09-05 倒置后行为翻转）→ has_assessment=False 且仍返回
        完整路径结构，assessment=None；recommendation/interpretation 诚实引导补全，
        不再是短 message 响应（原 test_no_assessment_steers_user 锁定的旧行为已废）。"""
        resp = client.post(self._post, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["has_assessment"] is False
        assert data["assessment"] is None
        assert isinstance(data["paths"], list)
        assert "测评" in data["interpretation"]["reason"]
        assert "个人档案" in data["recommendation"]

    def test_holland_interpret_honest_empty_paths(self, auth_headers, client):
        """有霍兰德测评、无画像 → 给出方向偏好，专有数据诚实为空（不造假数字）。"""
        client.post(
            "/api/assessment/submit",
            headers=auth_headers,
            json={"answers": _full_answers("q", ["R", "I", "A"], count=48)},
        )
        resp = client.post(self._post, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["has_assessment"] is True
        assert data["assessment"]["type"] == "holland"
        assert data["interpretation"]["primary_lean"] in {"kaoyan", "civil_service", "employment"}
        assert data["interpretation"]["reason"]
        # 无画像（专业/学校层次空）→ 三路为空但结构稳定，recommendation 给出引导
        assert isinstance(data["paths"], list)
        assert data["recommendation"]

    def test_interpret_with_profile_major(self, auth_headers, client, db_session):
        """有测评 + 画像专业 → 走真实决策引擎，input 正确回显专业。"""
        from app.models.career_profile import CareerProfile

        client.post(
            "/api/assessment/submit",
            headers=auth_headers,
            json={"answers": _full_answers("q", ["S", "E"], count=48)},
        )
        # 直接给当前用户建画像（auth_headers 已注册并登录）
        user_id = client.get("/api/auth/me", headers=auth_headers).json()["id"]
        db_session.add(
            CareerProfile(
                user_id=user_id,
                major="计算机",
                school_tier="211",
                education_level="本科",
                graduation_year=2026,
            )
        )
        db_session.commit()

        resp = client.post(self._post, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["profile"]["major"] == "计算机"
        assert data["input"]["major"] == "计算机"
        assert data["input"]["school_tier"] == "211"
        assert isinstance(data["data_notes"], list)
        assert len(data["data_notes"]) > 0
