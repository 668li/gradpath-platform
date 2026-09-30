"""决策深度分析测试 — 预验尸 LLM 降级兜底 + ai-analysis 错误契约（夜班修复轮1）。

覆盖（docs/夜班勘探-2026-10-01.md P0-2 / P0-3）：
- analyze_premortem：LLM 挂掉/输出不可解析时降级为模板聚类（ai_used=False），绝不裸 500
- analyze_premortem：LLM 正常时输出归一化为前端契约（categories[].category + safeguards[]）
- POST /{id}/ai-analysis：LLM 异常 → 503 AI_UNAVAILABLE（不再裸 500），不存在 → 404
"""

import json

import httpx

from app.services import decision_analysis_service
from app.services.ai_circuit_breaker import AICircuitBreakerOpenError
from app.services.ai_service import AIServiceNotConfigured, AIServiceRetryExhausted


# ----------------------------------------------------------------------
# 辅助：把 AIOrchestrator 替换为可编程假体
# ----------------------------------------------------------------------
def _patch_chat(monkeypatch, *, error: Exception | None = None, payload: str = ""):
    class _FakeOrchestrator:
        def __init__(self, *args, **kwargs):
            pass

        async def chat(self, system_prompt: str, user_prompt: str, timeout: int = 30) -> str:
            if error is not None:
                raise error
            return payload

    monkeypatch.setattr(decision_analysis_service, "AIOrchestrator", _FakeOrchestrator)


# ----------------------------------------------------------------------
# 预验尸：模板兜底（服务层）
# ----------------------------------------------------------------------
class TestPremortemDegradation:
    async def test_llm_down_degrades_to_template(self, monkeypatch):
        _patch_chat(monkeypatch, error=RuntimeError("dashscope arrearage"))
        result = await decision_analysis_service.analyze_premortem(
            "考研 vs 就业",
            ["考研", "直接就业"],
            [
                "复习时间不够",
                "家里经济压力大",
                "竞争太激烈报录比飙升",
                "完全重复的一条",
                "完全重复的一条",
            ],
        )
        assert result["ai_used"] is False
        cats = result["categories"]
        assert 1 <= len(cats) <= 5
        # 去重生效
        all_reasons = [r for c in cats for r in c["reasons"]]
        assert len(all_reasons) == len(set(all_reasons))
        # 关键词聚类命中
        by_name = {c["category"]: c for c in cats}
        assert any("时间" in n for n in by_name)
        assert any("经济" in n for n in by_name)
        # safeguards 与 categories 一一对应且动作非空
        assert [s["category"] for s in result["safeguards"]] == [c["category"] for c in cats]
        assert all(s["action"].strip() for s in result["safeguards"])

    async def test_llm_garbage_output_degrades(self, monkeypatch):
        _patch_chat(monkeypatch, payload="抱歉，我无法输出 JSON。")
        result = await decision_analysis_service.analyze_premortem(
            "转行", ["转码农", "留原行业"], ["存款只够撑三个月"]
        )
        assert result["ai_used"] is False
        assert result["categories"]

    async def test_llm_empty_categories_degrades(self, monkeypatch):
        _patch_chat(monkeypatch, payload=json.dumps({"categories": []}))
        result = await decision_analysis_service.analyze_premortem(
            "转行", ["转码农", "留原行业"], ["能力基础不足"]
        )
        assert result["ai_used"] is False
        assert result["categories"]


# ----------------------------------------------------------------------
# 预验尸：LLM 正常路径的契约归一化
# ----------------------------------------------------------------------
class TestPremortemNormalization:
    async def test_llm_shape_normalized_to_frontend_contract(self, monkeypatch):
        _patch_chat(
            monkeypatch,
            payload=json.dumps(
                {
                    "categories": [
                        {"name": "经济风险", "reasons": ["存款不足"], "safeguard": "备 6 个月预算"}
                    ]
                }
            ),
        )
        result = await decision_analysis_service.analyze_premortem(
            "转行", ["转码农", "留原行业"], ["存款不足"]
        )
        assert result["ai_used"] is True
        assert result["categories"][0]["category"] == "经济风险"
        assert result["categories"][0]["reasons"] == ["存款不足"]
        assert result["safeguards"][0] == {"category": "经济风险", "action": "备 6 个月预算"}

    async def test_llm_entries_without_name_skipped(self, monkeypatch):
        _patch_chat(
            monkeypatch,
            payload=json.dumps(
                {
                    "categories": [
                        {"reasons": ["无名字的类"], "safeguard": "x"},
                        {"name": "健康风险", "reasons": ["熬夜"], "safeguard": "规律作息"},
                    ]
                }
            ),
        )
        result = await decision_analysis_service.analyze_premortem(
            "转行", ["转码农", "留原行业"], ["熬夜"]
        )
        assert result["ai_used"] is True
        assert [c["category"] for c in result["categories"]] == ["健康风险"]


# ----------------------------------------------------------------------
# API 层：预验尸不再 500 / ai-analysis 503 契约
# ----------------------------------------------------------------------
class TestDecisionAnalysisApi:
    def test_premortem_api_returns_200_with_template_when_llm_down(
        self, client, auth_headers, monkeypatch
    ):
        _patch_chat(monkeypatch, error=AICircuitBreakerOpenError("breaker open"))
        resp = client.post(
            "/api/decision-analysis/premortem-analyze",
            headers=auth_headers,
            json={
                "title": "考研 vs 就业",
                "options": ["考研", "直接就业"],
                "premortem_reasons": ["复习时间不够", "竞争太激烈"],
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ai_used"] is False
        assert body["categories"]

    def test_ai_analysis_503_when_llm_unavailable(self, client, auth_headers, monkeypatch):
        create = client.post(
            "/api/decision-analysis/create",
            headers=auth_headers,
            json={"title": "是否考研", "options": ["考研", "就业"]},
        )
        assert create.status_code == 201
        analysis_id = create.json()["id"]

        _patch_chat(
            monkeypatch,
            error=httpx.HTTPStatusError(
                "LLM upstream HTTP 400: Arrearage",
                request=httpx.Request("POST", "https://llm.example/v1/chat"),
                response=httpx.Response(400),
            ),
        )
        resp = client.post(
            f"/api/decision-analysis/{analysis_id}/ai-analysis", headers=auth_headers
        )
        assert resp.status_code == 503
        body = resp.json()
        assert body["code"] == "AI_UNAVAILABLE"
        assert "AI 服务暂不可用" in body["detail"]

    def test_ai_analysis_503_when_retry_exhausted(self, client, auth_headers, monkeypatch):
        create = client.post(
            "/api/decision-analysis/create",
            headers=auth_headers,
            json={"title": "是否考公", "options": ["考公", "就业"]},
        )
        analysis_id = create.json()["id"]

        _patch_chat(
            monkeypatch,
            error=AIServiceRetryExhausted(TimeoutError("llm timeout")),
        )
        resp = client.post(
            f"/api/decision-analysis/{analysis_id}/ai-analysis", headers=auth_headers
        )
        assert resp.status_code == 503

    def test_ai_analysis_503_when_not_configured(self, client, auth_headers, monkeypatch):
        create = client.post(
            "/api/decision-analysis/create",
            headers=auth_headers,
            json={"title": "是否考公", "options": ["考公", "就业"]},
        )
        analysis_id = create.json()["id"]

        _patch_chat(monkeypatch, error=AIServiceNotConfigured("LLM_API_KEY 未配置"))
        resp = client.post(
            f"/api/decision-analysis/{analysis_id}/ai-analysis", headers=auth_headers
        )
        assert resp.status_code == 503

    def test_ai_analysis_404_when_missing(self, client, auth_headers, monkeypatch):
        _patch_chat(monkeypatch, error=RuntimeError("不应被触达"))
        resp = client.post(
            "/api/decision-analysis/00000000-0000-0000-0000-000000000000/ai-analysis",
            headers=auth_headers,
        )
        assert resp.status_code == 404
