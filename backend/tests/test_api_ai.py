# backend/tests/test_api_ai.py
"""AI 决策指导 API 测试。"""
import json
from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.models.career_event import CareerEvent, EventType
from app.models.company import Company, CompanySize
from app.models.salary_benchmark import ExperienceLevel, SalaryBenchmark
from app.models.skill_node import SkillNode
from datetime import date


# ======================================================================
# 辅助函数与测试数据
# ======================================================================

MOCK_LLM_RESPONSE = json.dumps(
    {
        "summary": "腾讯后端开发是一个高竞争力但回报丰厚的选择",
        "pros": ["薪资水平高于行业平均", "技术成长空间大"],
        "cons": ["竞争激烈，面试难度高", "工作强度大"],
        "market_analysis": "深圳互联网后端市场需求旺盛，腾讯头部地位稳固",
        "alternatives": [
            {"option": "字节跳动后端开发", "reason": "薪资相近，技术栈现代化"}
        ],
        "skill_gap": ["分布式系统设计", "高并发处理经验"],
        "confidence": 4,
        "advice": "建议补充分布式系统项目经验，重点准备系统设计面试。",
    },
    ensure_ascii=False,
)

MOCK_LLM_RESPONSE_MARKDOWN = (
    "以下是分析结果：\n"
    "```json\n"
    + json.dumps(
        {
            "summary": "阿里算法岗位前景广阔",
            "pros": ["AI赛道火热", "阿里达摩院技术积累深厚"],
            "cons": ["对论文与工程能力双重要求"],
            "market_analysis": "算法工程师供需两旺",
            "alternatives": [{"option": "腾讯AI Lab", "reason": "研究方向更前沿"}],
            "skill_gap": ["Transformer原理", "CUDA编程"],
            "confidence": 3,
            "advice": "建议补强论文产出与工程落地能力。",
        },
        ensure_ascii=False,
    )
    + "\n```\n"
)


def _seed_market_data(db_session):
    """预置外部市场数据供 context 组装测试。"""
    db_session.add(
        Company(
            name="腾讯",
            industry="互联网",
            size=CompanySize.giant,
            stage="已上市",
            headquarters="深圳",
            description="中国领先的互联网公司",
        )
    )
    db_session.add(
        SalaryBenchmark(
            company="腾讯",
            position="后端开发",
            city="深圳",
            experience_level=ExperienceLevel.entry,
            salary_min=18000,
            salary_median=22000,
            salary_max=28000,
            source="kaggle",
            year=2024,
        )
    )
    db_session.commit()


def _seed_user_profile(db_session, user_id):
    """预置用户画像数据（技能 + 职业事件）。"""
    db_session.add(
        SkillNode(
            user_id=user_id,
            name="Python",
            category="编程语言",
            level=4,
        )
    )
    db_session.add(
        CareerEvent(
            user_id=user_id,
            event_date=date(2024, 6, 1),
            event_type=EventType.project_done,
            title="完成毕业设计：分布式爬虫系统",
        )
    )
    db_session.commit()


def _advice_payload(**overrides):
    """构造决策指导请求体。"""
    payload = {
        "destination_type": "employment",
        "company": "腾讯",
        "position": "后端开发",
        "city": "深圳",
        "expected_salary": "25k_50k",
    }
    payload.update(overrides)
    return payload


# ======================================================================
# 权限控制
# ======================================================================

class TestAuth:
    def test_anonymous_decision_advice_fails(self, client):
        """未登录不能调用 AI 决策指导。"""
        resp = client.post("/api/ai/decision-advice", json=_advice_payload())
        assert resp.status_code == 401


# ======================================================================
# 降级策略
# ======================================================================

class TestDegradation:
    def test_no_llm_key_returns_503(self, auth_headers, client, db_session, monkeypatch):
        """LLM_API_KEY 未配置时返回 503。"""
        # 确保配置为空
        from app.services import ai_service

        monkeypatch.setattr(ai_service.settings, "LLM_API_KEY", "")

        resp = client.post(
            "/api/ai/decision-advice", headers=auth_headers, json=_advice_payload()
        )
        assert resp.status_code == 503
        assert "未配置" in resp.json()["detail"]

    def test_llm_timeout_returns_504(self, auth_headers, client, db_session, monkeypatch):
        """LLM 超时返回 504。"""
        # 配置一个假 key 使其通过 _check_config
        from app.services import ai_service

        monkeypatch.setattr(ai_service.settings, "LLM_API_KEY", "fake-key-for-test")

        with patch("app.services.ai_service.httpx.post") as mock_post:
            mock_post.side_effect = httpx.TimeoutException("request timed out")
            resp = client.post(
                "/api/ai/decision-advice",
                headers=auth_headers,
                json=_advice_payload(),
            )
        assert resp.status_code == 504
        assert "超时" in resp.json()["detail"]


# ======================================================================
# 正常调用
# ======================================================================

class TestNormalCall:
    def test_normal_call_with_mock_llm(self, auth_headers, client, db_session, monkeypatch):
        """正常调用（mock httpx.post 返回固定 JSON）。"""
        from app.services import ai_service

        monkeypatch.setattr(ai_service.settings, "LLM_API_KEY", "fake-key-for-test")

        _seed_market_data(db_session)

        with patch("app.services.ai_service.httpx.post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "choices": [{"message": {"content": MOCK_LLM_RESPONSE}}]
            }
            mock_response.raise_for_status = MagicMock()
            mock_post.return_value = mock_response

            resp = client.post(
                "/api/ai/decision-advice",
                headers=auth_headers,
                json=_advice_payload(),
            )

        assert resp.status_code == 200
        data = resp.json()
        assert "腾讯" in data["summary"]
        assert len(data["pros"]) == 2
        assert len(data["cons"]) == 2
        assert "分布式系统设计" in data["skill_gap"]
        assert data["confidence"] == 4
        assert len(data["alternatives"]) == 1
        assert data["alternatives"][0]["option"] == "字节跳动后端开发"

        # 验证 httpx.post 被调用且 payload 结构正确
        assert mock_post.called
        call_kwargs = mock_post.call_args.kwargs
        assert "json" in call_kwargs
        payload = call_kwargs["json"]
        assert payload["model"] == ai_service.settings.LLM_MODEL
        # messages 应包含 system + user
        assert len(payload["messages"]) == 2
        assert payload["messages"][0]["role"] == "system"
        assert payload["messages"][1]["role"] == "user"

    def test_markdown_codeblock_json_parsed(self, auth_headers, client, db_session, monkeypatch):
        """LLM 返回带 markdown 代码块的 JSON 也能正确解析。"""
        from app.services import ai_service

        monkeypatch.setattr(ai_service.settings, "LLM_API_KEY", "fake-key-for-test")

        with patch("app.services.ai_service.httpx.post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "choices": [{"message": {"content": MOCK_LLM_RESPONSE_MARKDOWN}}]
            }
            mock_response.raise_for_status = MagicMock()
            mock_post.return_value = mock_response

            resp = client.post(
                "/api/ai/decision-advice",
                headers=auth_headers,
                json=_advice_payload(company="阿里巴巴", position="算法工程师"),
            )

        assert resp.status_code == 200
        data = resp.json()
        assert "阿里" in data["summary"]
        assert data["confidence"] == 3
        assert "Transformer原理" in data["skill_gap"]

    def test_non_json_response_fallback_to_advice(
        self, auth_headers, client, db_session, monkeypatch
    ):
        """LLM 返回非 JSON 时，原始文本放入 advice 字段。"""
        from app.services import ai_service

        monkeypatch.setattr(ai_service.settings, "LLM_API_KEY", "fake-key-for-test")

        plain_text = "抱歉，我无法生成结构化建议，但建议你考虑自身兴趣与市场需求的平衡。"

        with patch("app.services.ai_service.httpx.post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "choices": [{"message": {"content": plain_text}}]
            }
            mock_response.raise_for_status = MagicMock()
            mock_post.return_value = mock_response

            resp = client.post(
                "/api/ai/decision-advice",
                headers=auth_headers,
                json=_advice_payload(),
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["advice"] == plain_text
        assert data["pros"] == []
        assert data["cons"] == []
        assert data["confidence"] == 1


# ======================================================================
# Context 组装逻辑
# ======================================================================

class TestContextAssembly:
    def test_user_context_assembled(self, auth_headers, client, db_session, monkeypatch):
        """验证用户画像（技能、职业事件）被正确查询并注入 context。"""
        from app.services import ai_service

        monkeypatch.setattr(ai_service.settings, "LLM_API_KEY", "fake-key-for-test")

        # 获取当前用户 ID
        from app.models.user import User

        user = db_session.query(User).filter(User.email == "test@example.com").first()
        _seed_user_profile(db_session, user.id)

        captured_content = {}

        def fake_chat(self, system_prompt, user_content, timeout=30):
            captured_content["system"] = system_prompt
            captured_content["user"] = user_content
            return MOCK_LLM_RESPONSE

        with patch.object(ai_service.AIService, "chat", fake_chat):
            resp = client.post(
                "/api/ai/decision-advice",
                headers=auth_headers,
                json=_advice_payload(),
            )

        assert resp.status_code == 200
        user_content = captured_content["user"]
        # 用户画像应包含技能与职业事件
        assert "Python" in user_content
        assert "分布式爬虫系统" in user_content
        assert "【用户画像】" in user_content

    def test_market_context_assembled(self, auth_headers, client, db_session, monkeypatch):
        """验证市场数据（公司元数据、薪资基准）被正确查询并注入 context。"""
        from app.services import ai_service

        monkeypatch.setattr(ai_service.settings, "LLM_API_KEY", "fake-key-for-test")

        _seed_market_data(db_session)

        captured_content = {}

        def fake_chat(self, system_prompt, user_content, timeout=30):
            captured_content["user"] = user_content
            return MOCK_LLM_RESPONSE

        with patch.object(ai_service.AIService, "chat", fake_chat):
            resp = client.post(
                "/api/ai/decision-advice",
                headers=auth_headers,
                json=_advice_payload(),
            )

        assert resp.status_code == 200
        user_content = captured_content["user"]
        # 公司元数据
        assert "腾讯" in user_content
        assert "互联网" in user_content
        # 薪资基准
        assert "22000" in user_content or "18000" in user_content
        assert "【市场数据】" in user_content

    def test_community_context_assembled(self, auth_headers, client, db_session, monkeypatch):
        """验证社区数据（面试经验、同类人去向）被正确查询并注入 context。"""
        from app.services import ai_service

        monkeypatch.setattr(ai_service.settings, "LLM_API_KEY", "fake-key-for-test")

        # 预置面试经验数据
        from app.models.user import User
        from app.models.interview_report import (
            InterviewReport,
            InterviewResult,
        )
        from app.models.community_report import (
            CommunityReport,
            DestinationType,
            SalaryRange,
        )

        user = db_session.query(User).filter(User.email == "test@example.com").first()
        db_session.add(
            InterviewReport(
                user_id=user.id,
                company="腾讯",
                position="后端开发",
                interview_year=2024,
                city="深圳",
                rounds=3,
                result=InterviewResult.offer,
                dimensions=["algorithm", "system_design"],
                difficulty=4,
                summary="侧重算法",
            )
        )
        db_session.add(
            CommunityReport(
                user_id=user.id,
                school_name="清华大学",
                major="计算机科学",
                graduation_year=2024,
                destination_type=DestinationType.employment,
                employer="腾讯",
                city="深圳",
                industry="互联网",
                salary_range=SalaryRange.r25k_50k,
            )
        )
        db_session.commit()

        captured_content = {}

        def fake_chat(self, system_prompt, user_content, timeout=30):
            captured_content["user"] = user_content
            return MOCK_LLM_RESPONSE

        with patch.object(ai_service.AIService, "chat", fake_chat):
            resp = client.post(
                "/api/ai/decision-advice",
                headers=auth_headers,
                json=_advice_payload(),
            )

        assert resp.status_code == 200
        user_content = captured_content["user"]
        assert "【社区参考】" in user_content
        # 面试经验
        assert "面试经验" in user_content
        # 同类人去向
        assert "同类人去向" in user_content

    def test_context_priority_order(self, auth_headers, client, db_session, monkeypatch):
        """验证 context 拼装顺序：用户画像 > 薪资基准 > 社区数据 > 市场趋势。"""
        from app.services import ai_service

        monkeypatch.setattr(ai_service.settings, "LLM_API_KEY", "fake-key-for-test")

        captured_content = {}

        def fake_chat(self, system_prompt, user_content, timeout=30):
            captured_content["user"] = user_content
            return MOCK_LLM_RESPONSE

        with patch.object(ai_service.AIService, "chat", fake_chat):
            resp = client.post(
                "/api/ai/decision-advice",
                headers=auth_headers,
                json=_advice_payload(),
            )

        assert resp.status_code == 200
        user_content = captured_content["user"]
        pos_user = user_content.find("【用户画像】")
        pos_market = user_content.find("【市场数据】")
        pos_community = user_content.find("【社区参考】")
        pos_request = user_content.find("【用户决策请求】")
        assert pos_user < pos_market < pos_community < pos_request


# ======================================================================
# AI 成长洞察
# ======================================================================

MOCK_GROWTH_INSIGHT_RESPONSE = json.dumps(
    {
        "growth_score": 78,
        "trend": "rising",
        "strengths": ["技术深度持续提升", "项目交付能力强"],
        "gaps": ["跨团队沟通能力", "系统设计经验"],
        "recommendations": ["参与架构设计评审", "定期与跨团队对齐目标"],
        "summary": "该时段成长势头良好，技术能力稳步提升，建议加强系统设计与跨团队协作。",
    },
    ensure_ascii=False,
)


def _seed_events_for_growth(db_session, user_id, count=2, base_date=date(2025, 6, 1)):
    """预置指定数量的职业事件（用于成长洞察 context 与缓存测试）。"""
    for i in range(count):
        db_session.add(
            CareerEvent(
                user_id=user_id,
                event_date=base_date,
                event_type=EventType.project_done,
                title=f"成长事件_{i + 1}",
            )
        )
    db_session.commit()


def _growth_insight_payload(**overrides):
    """构造成长洞察请求体。"""
    payload = {
        "period_start": "2025-01-01",
        "period_end": "2025-12-31",
    }
    payload.update(overrides)
    return payload


class TestGrowthInsightAuth:
    def test_anonymous_growth_insight_fails(self, client):
        """未登录不能调用成长洞察。"""
        resp = client.post("/api/ai/growth-insight", json=_growth_insight_payload())
        assert resp.status_code == 401

    def test_anonymous_latest_insight_fails(self, client):
        """未登录不能获取最新洞察。"""
        resp = client.get("/api/ai/growth-insight/latest")
        assert resp.status_code == 401


class TestGrowthInsightDegradation:
    def test_no_llm_key_returns_503(self, auth_headers, client, db_session, monkeypatch):
        """LLM_API_KEY 未配置时返回 503。"""
        from app.services import ai_service

        monkeypatch.setattr(ai_service.settings, "LLM_API_KEY", "")

        resp = client.post(
            "/api/ai/growth-insight",
            headers=auth_headers,
            json=_growth_insight_payload(),
        )
        assert resp.status_code == 503
        assert "未配置" in resp.json()["detail"]

    def test_llm_timeout_returns_504(self, auth_headers, client, db_session, monkeypatch):
        """LLM 超时返回 504。"""
        from app.services import ai_service

        monkeypatch.setattr(ai_service.settings, "LLM_API_KEY", "fake-key-for-test")

        def fake_chat(self, system_prompt, user_content, timeout=30):
            raise httpx.TimeoutException("request timed out")

        with patch.object(ai_service.AIService, "chat", fake_chat):
            resp = client.post(
                "/api/ai/growth-insight",
                headers=auth_headers,
                json=_growth_insight_payload(),
            )
        assert resp.status_code == 504
        assert "超时" in resp.json()["detail"]


class TestGrowthInsightNormalCall:
    def test_success_with_mock_llm(self, auth_headers, client, db_session, monkeypatch):
        """正常调用（mock AIService.chat 返回固定 JSON）。"""
        from app.models.user import User
        from app.services import ai_service

        monkeypatch.setattr(ai_service.settings, "LLM_API_KEY", "fake-key-for-test")

        user = db_session.query(User).filter(User.email == "test@example.com").first()
        _seed_events_for_growth(db_session, user.id, count=2)

        with patch.object(
            ai_service.AIService,
            "chat",
            lambda self, sp, uc, timeout=30: MOCK_GROWTH_INSIGHT_RESPONSE,
        ):
            resp = client.post(
                "/api/ai/growth-insight",
                headers=auth_headers,
                json=_growth_insight_payload(),
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["growth_score"] == 78
        assert data["trend"] == "rising"
        assert len(data["strengths"]) == 2
        assert len(data["gaps"]) == 2
        assert len(data["recommendations"]) == 2
        assert "成长势头" in data["summary"]

    def test_cache_hit_skips_llm_call(self, auth_headers, client, db_session, monkeypatch):
        """相同 period + event_count 时命中缓存，不重复调用 LLM。"""
        from app.models.user import User
        from app.services import ai_service

        monkeypatch.setattr(ai_service.settings, "LLM_API_KEY", "fake-key-for-test")

        user = db_session.query(User).filter(User.email == "test@example.com").first()
        _seed_events_for_growth(db_session, user.id, count=2)

        call_count = {"n": 0}

        def fake_chat(self, system_prompt, user_content, timeout=30):
            call_count["n"] += 1
            return MOCK_GROWTH_INSIGHT_RESPONSE

        with patch.object(ai_service.AIService, "chat", fake_chat):
            resp1 = client.post(
                "/api/ai/growth-insight",
                headers=auth_headers,
                json=_growth_insight_payload(),
            )
            resp2 = client.post(
                "/api/ai/growth-insight",
                headers=auth_headers,
                json=_growth_insight_payload(),
            )

        assert resp1.status_code == 200
        assert resp2.status_code == 200
        # 缓存命中：LLM 仅调用一次
        assert call_count["n"] == 1
        # 两次返回结果一致
        assert resp1.json() == resp2.json()

    def test_cache_miss_on_event_count_change(self, auth_headers, client, db_session, monkeypatch):
        """event_count 变化时缓存未命中，重新调用 LLM。"""
        from app.models.user import User
        from app.services import ai_service

        monkeypatch.setattr(ai_service.settings, "LLM_API_KEY", "fake-key-for-test")

        user = db_session.query(User).filter(User.email == "test@example.com").first()
        _seed_events_for_growth(db_session, user.id, count=2)

        call_count = {"n": 0}

        def fake_chat(self, system_prompt, user_content, timeout=30):
            call_count["n"] += 1
            return MOCK_GROWTH_INSIGHT_RESPONSE

        with patch.object(ai_service.AIService, "chat", fake_chat):
            # 第一次调用：2 个事件
            resp1 = client.post(
                "/api/ai/growth-insight",
                headers=auth_headers,
                json=_growth_insight_payload(),
            )
            # 新增一个事件（event_count 变为 3）
            _seed_events_for_growth(db_session, user.id, count=1)
            # 第二次调用：缓存未命中，重新调用 LLM
            resp2 = client.post(
                "/api/ai/growth-insight",
                headers=auth_headers,
                json=_growth_insight_payload(),
            )

        assert resp1.status_code == 200
        assert resp2.status_code == 200
        # 缓存未命中：LLM 调用两次
        assert call_count["n"] == 2


class TestGrowthInsightLatest:
    def test_latest_returns_404_when_no_insight(self, auth_headers, client):
        """无洞察记录时返回 404。"""
        resp = client.get("/api/ai/growth-insight/latest", headers=auth_headers)
        assert resp.status_code == 404

    def test_latest_returns_cached_insight(self, auth_headers, client, db_session, monkeypatch):
        """生成洞察后，GET latest 返回缓存结果。"""
        from app.models.user import User
        from app.services import ai_service

        monkeypatch.setattr(ai_service.settings, "LLM_API_KEY", "fake-key-for-test")

        user = db_session.query(User).filter(User.email == "test@example.com").first()
        _seed_events_for_growth(db_session, user.id, count=1)

        with patch.object(
            ai_service.AIService,
            "chat",
            lambda self, sp, uc, timeout=30: MOCK_GROWTH_INSIGHT_RESPONSE,
        ):
            # 先生成一次洞察
            client.post(
                "/api/ai/growth-insight",
                headers=auth_headers,
                json=_growth_insight_payload(),
            )

        # 查询最新洞察（无需 mock，走缓存 / 直接返回 DB 记录）
        resp = client.get("/api/ai/growth-insight/latest", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["growth_score"] == 78
        assert data["trend"] == "rising"
