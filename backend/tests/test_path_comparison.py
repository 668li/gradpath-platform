# backend/tests/test_path_comparison.py
"""多路径 What-If 对比 API 测试 — compare / history。"""


# ----------------------------------------------------------------------
# 辅助：构造路径请求
# ----------------------------------------------------------------------
def _paths_two() -> list[dict]:
    return [
        {"path_type": "kaoyan", "target_role": "算法工程师"},
        {"path_type": "employment", "target_role": "后端开发"},
    ]


def _paths_three() -> list[dict]:
    return [
        {"path_type": "kaoyan", "target_role": "算法工程师"},
        {"path_type": "civil_service", "target_role": "选调生"},
        {"path_type": "big_tech", "target_role": "大厂后端"},
    ]


# Holland RIA 答案 — 推荐技术/研究类方向
_RIA_ANSWERS = {
    "q1": "R", "q2": "I", "q3": "A", "q4": "R",
    "q5": "I", "q6": "A", "q7": "R", "q8": "I",
    "q9": "A", "q10": "R", "q11": "I", "q12": "A",
}


def _submit_assessment(client, auth_headers, answers: dict):
    """提交一次测评，返回响应 JSON。"""
    resp = client.post(
        "/api/assessment/submit",
        headers=auth_headers,
        json={"answers": answers},
    )
    assert resp.status_code == 201, f"测评提交失败: {resp.text}"
    return resp.json()


# ----------------------------------------------------------------------
# compare 端点
# ----------------------------------------------------------------------
class TestComparePaths:
    def test_compare_requires_auth(self, client):
        """compare 端点必须带 token。"""
        resp = client.post(
            "/api/path-comparison/compare",
            json={"paths": _paths_two()},
        )
        assert resp.status_code == 401

    def test_compare_two_paths(self, auth_headers, client):
        """2 条路径对比应成功返回量化指标。"""
        resp = client.post(
            "/api/path-comparison/compare",
            headers=auth_headers,
            json={"paths": _paths_two()},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["id"]
        assert len(data["metrics"]) == 2
        assert data["recommendation"]
        assert data["created_at"]

    def test_compare_three_paths(self, auth_headers, client):
        """3 条路径对比应成功返回量化指标。"""
        resp = client.post(
            "/api/path-comparison/compare",
            headers=auth_headers,
            json={"paths": _paths_three()},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert len(data["metrics"]) == 3
        # 3 条路径类型应分别为 kaoyan / civil_service / big_tech
        types = {m["path_type"] for m in data["metrics"]}
        assert types == {"kaoyan", "civil_service", "big_tech"}

    def test_compare_rejects_single_path(self, auth_headers, client):
        """只给 1 条路径应返回 422。"""
        resp = client.post(
            "/api/path-comparison/compare",
            headers=auth_headers,
            json={"paths": [{"path_type": "kaoyan", "target_role": "算法工程师"}]},
        )
        assert resp.status_code == 422

    def test_compare_rejects_four_paths(self, auth_headers, client):
        """给 4 条路径应返回 422。"""
        paths = _paths_three() + [{"path_type": "startup", "target_role": "SaaS 创业"}]
        resp = client.post(
            "/api/path-comparison/compare",
            headers=auth_headers,
            json={"paths": paths},
        )
        assert resp.status_code == 422

    def test_metrics_fields_complete(self, auth_headers, client):
        """每条路径的 metrics 字段应完整。"""
        resp = client.post(
            "/api/path-comparison/compare",
            headers=auth_headers,
            json={"paths": _paths_two()},
        )
        data = resp.json()
        required = {
            "path_type", "target_role",
            "income_1y", "income_3y", "income_5y",
            "risk_level", "risk_description",
            "growth_score", "time_cost_months",
            "match_score", "match_description",
            "pros", "cons",
        }
        for m in data["metrics"]:
            missing = required - set(m.keys())
            assert not missing, f"metrics 缺少字段: {missing}"
            assert m["risk_level"] in ("low", "medium", "high")
            assert 1 <= m["growth_score"] <= 10
            assert 0 <= m["match_score"] <= 100
            assert m["time_cost_months"] >= 0
            assert isinstance(m["pros"], list) and len(m["pros"]) > 0
            assert isinstance(m["cons"], list) and len(m["cons"]) > 0

    def test_recommendation_non_empty(self, auth_headers, client):
        """综合建议文本不应为空。"""
        resp = client.post(
            "/api/path-comparison/compare",
            headers=auth_headers,
            json={"paths": _paths_three()},
        )
        data = resp.json()
        assert data["recommendation"]
        # 综合建议应包含「如果追求」关键字
        assert "如果追求" in data["recommendation"]

    def test_compare_with_assessment_uses_holland(self, auth_headers, client):
        """有测评数据时，匹配度应基于霍兰德代码计算（推荐方向命中加分）。"""
        _submit_assessment(client, auth_headers, _RIA_ANSWERS)
        resp = client.post(
            "/api/path-comparison/compare",
            headers=auth_headers,
            json={"paths": _paths_two()},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        # 至少有一条 match_description 包含「霍兰德」
        descriptions = [m["match_description"] for m in data["metrics"]]
        assert any("霍兰德" in d for d in descriptions), descriptions

    def test_compare_unknown_path_type_falls_back(self, auth_headers, client):
        """未知 path_type 应兜底为 employment。"""
        resp = client.post(
            "/api/path-comparison/compare",
            headers=auth_headers,
            json={
                "paths": [
                    {"path_type": "unknown_xyz", "target_role": "神秘岗位"},
                    {"path_type": "employment", "target_role": "后端开发"},
                ]
            },
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        # 未知路径应被兜底为 employment
        assert data["metrics"][0]["path_type"] == "employment"


# ----------------------------------------------------------------------
# history 端点
# ----------------------------------------------------------------------
class TestHistory:
    def test_history_requires_auth(self, client):
        resp = client.get("/api/path-comparison/history")
        assert resp.status_code == 401

    def test_history_empty(self, auth_headers, client):
        """无历史记录时返回空列表。"""
        resp = client.get("/api/path-comparison/history", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_history_after_compare(self, auth_headers, client):
        """完成一次 compare 后，history 应包含该记录。"""
        client.post(
            "/api/path-comparison/compare",
            headers=auth_headers,
            json={"paths": _paths_two()},
        )
        client.post(
            "/api/path-comparison/compare",
            headers=auth_headers,
            json={"paths": _paths_three()},
        )

        resp = client.get("/api/path-comparison/history", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 2
        # 倒序：最新一次在前
        assert len(data[0]["metrics"]) == 3
        assert len(data[1]["metrics"]) == 2
        # 每条记录应有非空 recommendation
        for item in data:
            assert item["id"]
            assert item["recommendation"]
            assert item["created_at"]
            assert isinstance(item["metrics"], list)


# ----------------------------------------------------------------------
# 服务层单元测试（不依赖 HTTP）
# ----------------------------------------------------------------------
class TestServiceLayer:
    def test_generate_comparison_returns_metrics(self):
        from app.services.path_comparison_service import generate_comparison

        result = generate_comparison(_paths_two(), user_context=None)
        assert "metrics" in result
        assert "recommendation" in result
        assert len(result["metrics"]) == 2
        for m in result["metrics"]:
            assert m["risk_level"] in ("low", "medium", "high")
            assert 1 <= m["growth_score"] <= 10

    def test_generate_comparison_with_holland(self):
        from app.services.path_comparison_service import generate_comparison

        ctx = {
            "holland_code": "RIA",
            "recommended_directions": ["后端开发", "算法工程师"],
        }
        result = generate_comparison(_paths_two(), user_context=ctx)
        # 推荐方向命中 target_role 时，match_description 应包含「目标角色与测评推荐方向一致」
        # 且基于 holland 维度计算，匹配度应高于无测评时的兜底值
        for m in result["metrics"]:
            assert "霍兰德" in m["match_description"]
            if m["target_role"] in ("后端开发", "算法工程师"):
                assert "目标角色与测评推荐方向一致" in m["match_description"]
                # 命中推荐方向加 10 分；基础分至少 30 → 总分 ≥ 40
                assert m["match_score"] >= 40

    def test_get_recommendation_condition_style(self):
        from app.services.path_comparison_service import get_recommendation

        metrics = [
            {
                "path_type": "kaoyan", "target_role": "算法工程师",
                "income_1y": "0-5万", "income_3y": "15-25万", "income_5y": "25-40万",
                "risk_level": "high", "risk_description": "录取率低",
                "growth_score": 7, "time_cost_months": 12,
                "match_score": 65, "match_description": "匹配",
                "pros": [], "cons": [],
            },
            {
                "path_type": "big_tech", "target_role": "大厂后端",
                "income_1y": "20-35万", "income_3y": "35-55万", "income_5y": "50-80万",
                "risk_level": "medium", "risk_description": "竞争激烈",
                "growth_score": 9, "time_cost_months": 4,
                "match_score": 70, "match_description": "匹配",
                "pros": [], "cons": [],
            },
        ]
        rec = get_recommendation(metrics, holland_code="RIA")
        # 应包含 5 个维度的条件式建议关键字
        assert "如果追求收入上限" in rec
        assert "如果追求稳定低风险" in rec
        assert "如果追求成长性" in rec
        assert "如果时间成本敏感" in rec
        assert "如果追求与个人画像匹配" in rec
        # 应包含霍兰德代码
        assert "RIA" in rec
