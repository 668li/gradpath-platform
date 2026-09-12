# tests/test_data_search_service.py
"""站内数据搜索层测试 — 三段式查库注入。

09-12 策略转向：职位/考研复试线搜索器已随「不做职位库、考研线不投入」删除；
本文件覆盖保留面：公告（L2 核心）、薪资、市场 + 意图路由 + 诚实降级。
"""

from __future__ import annotations

import os
import sys

# 确保 backend/app 在 path 中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import pytest

from app.services.data_search_service import (
    detect_data_intents,
    extract_dept,
    extract_major,
    extract_schools,
    run_data_search,
    search_announcements,
)

# ======================================================================
# 参数抽取
# ======================================================================


class TestExtract:
    def test_extract_schools(self):
        assert extract_schools("我想考清华大学计算机研究生") == ["清华大学"]
        assert extract_schools("北京大学和中南大学哪个好") == ["北京大学", "中南大学"]
        assert extract_schools("帮我看看分数线") == []

    def test_extract_major(self):
        assert extract_major("计算机专业好考吗") == "计算机"
        assert extract_major("我学的是会计") == "会计"
        assert extract_major("帮我看看学校") is None
        # 学历前缀误吞回归（生产零命中事故）："本科计算机专业"→"计算机"
        assert extract_major("本科计算机专业能报什么岗位") == "计算机"
        assert extract_major("硕士研究生法学专业") == "法学"
        # 校名误吞回归
        assert extract_major("清华大学计算机专业分数线多少") == "计算机"

    def test_extract_dept(self):
        assert extract_dept("海关和国考税务哪个好") == "海关"  # 文本中最早出现优先
        assert extract_dept("随便看看") is None


# ======================================================================
# 代码级意图路由
# ======================================================================


class TestDetectIntents:
    def test_announcement_intent(self):
        intents = detect_data_intents("最新的招生简章出了吗")
        assert any(i.domain == "announcements" for i in intents)

    def test_announcement_intent_with_school_keyword(self):
        intents = detect_data_intents("清华大学研究生院发了什么公告")
        ann = next(i for i in intents if i.domain == "announcements")
        assert ann.params["keyword"] == "清华大学"

    def test_salary_intent(self):
        intents = detect_data_intents("计算机专业薪资怎么样")
        assert any(i.domain == "salary" for i in intents)

    def test_market_intent(self):
        intents = detect_data_intents("电气行业趋势如何")
        assert any(i.domain == "market" for i in intents)

    def test_no_data_intent(self):
        assert detect_data_intents("今天天气怎么样") == []


# ======================================================================
# 公告搜索器（KaoyanNews official + 暂存表兜底）
# ======================================================================


@pytest.fixture
def seed_announcement(db_session):
    from datetime import datetime

    from app.models.kaoyan_news import KaoyanNews

    row = KaoyanNews(
        title="测试大学 2027 年硕士研究生招生简章",
        summary="我校 2027 年拟招收硕士研究生 5000 名，计算机专业统考科目调整为 408。",
        content="全文……" * 10,
        source_platform="official",
        source_url="https://gs.test.edu.cn/zhaosheng",
        status="approved",
        category="官方公告·测试大学研究生院",
        published_at=datetime(2026, 9, 1, 10, 0, 0),
    )
    db_session.add(row)
    db_session.commit()
    return row


class TestAnnouncementSearcher:
    def test_search_hits_kaoyan_news(self, db_session, seed_announcement):
        hits = search_announcements(db_session, "测试大学")
        assert len(hits) == 1
        assert hits[0].url == "https://gs.test.edu.cn/zhaosheng"
        assert hits[0].year == 2026

    def test_search_no_keyword_returns_latest(self, db_session, seed_announcement):
        assert len(search_announcements(db_session, None)) == 1

    def test_search_empty_db_returns_empty(self, db_session):
        assert search_announcements(db_session, "不存在") == []

    def test_non_official_not_returned(self, db_session):
        """非 official 来源（rss/web）不算公告，不得混入。"""
        from datetime import datetime

        from app.models.kaoyan_news import KaoyanNews

        db_session.add(
            KaoyanNews(
                title="普通资讯",
                content="x",
                source_platform="rss",
                source_url="https://rss.example.com/a",
                status="approved",
                published_at=datetime(2026, 9, 1),
            )
        )
        db_session.commit()
        assert search_announcements(db_session, "普通资讯") == []


# ======================================================================
# run_data_search — 注入块与 sources
# ======================================================================


class TestRunDataSearch:
    def test_no_intent_returns_empty(self, db_session):
        block, sources, has_hits = run_data_search(db_session, "今天天气怎么样")
        assert block == "" and sources == [] and has_hits is False

    def test_intent_but_empty_honest_degradation(self, db_session):
        """检测到意图但库中无数据 → 明示禁编块 + 引导官方渠道。"""
        block, sources, has_hits = run_data_search(db_session, "清华大学研究生院最新公告")
        assert has_hits is False
        assert "禁止编造" in block
        assert "官方" in block
        assert sources == []

    def test_hits_block_contains_sources(self, db_session, seed_announcement):
        block, sources, has_hits = run_data_search(db_session, "测试大学的招生简章出了吗")
        assert has_hits is True
        assert "站内数据检索结果" in block
        assert "kaoyan_news" in block
        assert len(sources) == 1
        assert sources[0]["type"] == "db"

    def test_skip_domains_dedup(self, db_session, seed_announcement):
        """数据型 skill 已覆盖的域被跳过，不双注入。"""
        block, _, _ = run_data_search(
            db_session, "测试大学的招生简章出了吗", skip_domains={"announcements"}
        )
        assert block == ""


# ======================================================================
# chat 契约
# ======================================================================


def test_send_message_response_fields():
    from app.schemas.chat import SendMessageResponse

    resp = SendMessageResponse(
        content="基于真实数据的回答",
        skill_used="announcement_interpreter",
        career_plan=None,
        micro_action_plan="abc",
        agent_sources=[{"type": "db", "title": "某公告", "url": "https://x"}],
        agent_confidence=0.7,
    )
    assert resp.agent_sources[0]["type"] == "db"
    assert resp.micro_action_plan == "abc"
    legacy = SendMessageResponse(content="a", skill_used="default", career_plan=None)
    assert legacy.agent_sources is None and legacy.micro_action_plan is None
