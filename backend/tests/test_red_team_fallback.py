"""决策实验室红队质疑规则化降级测试 — LLM 不可用时零 LLM 也能出尖锐问题。"""

import pytest

from app.services.decision_analysis_service import (
    _heuristic_red_team_questions,
    generate_red_team_questions,
)


class TestHeuristicRedTeam:
    def test_embeds_user_options(self):
        """问题嵌入用户自己的选项文本，保证针对性。"""
        qs = _heuristic_red_team_questions("字节 vs 阿里", ["字节跳动", "阿里巴巴"], "薪资更高")
        assert len(qs) == 7
        assert any("字节跳动" in q for q in qs)
        assert any("阿里巴巴" in q for q in qs)

    def test_covers_core_frameworks(self):
        """五个核心框架（前提/替代/二阶/成本/可逆）各有落点。"""
        qs = _heuristic_red_team_questions("考研还是就业", ["考研", "就业"], None)
        joined = " ".join(qs)
        assert "假设" in joined
        assert "最强论据" in joined
        assert "6 个月" in joined
        assert "放弃" in joined or "成本" in joined
        assert "退回" in joined or "可逆" in joined

    def test_single_option_still_works(self):
        """只有一个选项时不出错（回退文本）。"""
        qs = _heuristic_red_team_questions("要不要裸辞", ["裸辞"], None)
        assert len(qs) == 7

    def test_no_placeholder_left(self):
        """问题文本无空占位符。"""
        qs = _heuristic_red_team_questions("T", ["A", "B"], None)
        assert all("{" not in q and "None" not in q for q in qs)


class TestRedTeamFallback:
    @pytest.mark.asyncio
    async def test_falls_back_when_llm_raises(self, monkeypatch):
        """LLM 抛异常时降级到规则化问题，不向用户抛错。"""

        async def boom(**kwargs):
            raise RuntimeError("LLM down")

        monkeypatch.setattr("app.services.decision_analysis_service.AIOrchestrator.chat", boom)
        qs = await generate_red_team_questions("T", ["A", "B"], None)
        assert len(qs) == 7

    @pytest.mark.asyncio
    async def test_falls_back_when_llm_returns_empty(self, monkeypatch):
        """LLM 返回空文本时同样降级。"""

        async def empty(**kwargs):
            return "   \n  "

        monkeypatch.setattr("app.services.decision_analysis_service.AIOrchestrator.chat", empty)
        qs = await generate_red_team_questions("T", ["A", "B"], None)
        assert len(qs) == 7
