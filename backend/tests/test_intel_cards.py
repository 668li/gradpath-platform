# tests/test_intel_cards.py
"""门道卡测试 — 批次 B+（2026-09-26 五问拍板：门道信息差·考研先行）。

覆盖 B9 验收契约（≥15 卡 ≥12 问 / 每卡带源 / 置信度三档）+ B10 chat 注入
（命中返回带源卡片、不命中不硬塞）+ seed 幂等。
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import pytest

from app.models.intel_card import (
    INTEL_CONFIDENCE_MULTI,
    INTEL_CONFIDENCE_OFFICIAL,
    INTEL_CONFIDENCE_SINGLE,
    IntelCard,
)
from app.services.data_search_service import (
    detect_data_intents,
    run_data_search,
)
from app.services.intel_card_seed import _CARDS, seed_intel_cards


@pytest.fixture()
def seeded_db(db_session):
    seed_intel_cards(db_session)
    return db_session


# ======================================================================
# B9 seed 数据质量门（验收契约锁：不足如实，禁止凑数）
# ======================================================================


class TestSeedQualityGate:
    def test_at_least_15_cards(self):
        assert len(_CARDS) >= 15, f"硬卡数 {len(_CARDS)} < 15，B9 验收不达标"

    def test_covers_at_least_12_questions(self):
        questions = {c["question_id"] for c in _CARDS}
        assert len(questions) >= 12, f"覆盖问题数 {len(questions)} < 12"

    def test_every_card_has_openable_sources(self):
        for c in _CARDS:
            assert c["sources"], f"卡 {c['question_id']}/{c['title']} 无来源"
            for s in c["sources"]:
                assert s["url"].startswith(("http://", "https://")), (
                    f"卡 {c['title']} 来源 URL 非法: {s['url']}"
                )
                assert s.get("supports"), f"卡 {c['title']} 来源缺支撑说明"

    def test_confidence_enum_and_no_unlabeled_single(self):
        valid = {INTEL_CONFIDENCE_OFFICIAL, INTEL_CONFIDENCE_MULTI, INTEL_CONFIDENCE_SINGLE}
        for c in _CARDS:
            assert c["confidence"] in valid, f"卡 {c['title']} 置信度非法: {c['confidence']}"
            if c["confidence"] == INTEL_CONFIDENCE_SINGLE:
                # 孤证卡必须卡面可辨（title 由页面强制加"孤证"徽章，此处锁数据面）
                assert len(c["sources"]) == 1, "孤证卡来源应恰为 1 条"

    def test_official_confidence_requires_authoritative_domain(self):
        """official 徽章纪律：来源链必须含官方域名直证，防媒体转述稀释徽章。"""
        _OFFICIAL_HINTS = (".gov.cn", ".edu.cn", "chsi.com.cn", "cnr.cn")
        for c in _CARDS:
            if c["confidence"] != INTEL_CONFIDENCE_OFFICIAL:
                continue
            domains = " ".join(s["url"] for s in c["sources"])
            assert any(h in domains for h in _OFFICIAL_HINTS), (
                f"卡 {c['title']} 标 official 但来源无官方域名直证"
            )


# ======================================================================
# seed 幂等与入库
# ======================================================================


class TestSeedIdempotent:
    def test_seed_twice_skips_all(self, seeded_db):
        inserted, skipped = seed_intel_cards(seeded_db)
        assert inserted == 0
        assert skipped == len(_CARDS)
        assert seeded_db.query(IntelCard).count() == len(_CARDS)

    def test_seed_writes_question_text(self, seeded_db):
        card = seeded_db.query(IntelCard).filter(IntelCard.question_id == "D2").first()
        assert card is not None
        assert "双非" in card.question_text
        assert card.track == "kaoyan"
        assert card.status == "active"


# ======================================================================
# B9 公开 API
# ======================================================================


class TestIntelCardsApi:
    def test_list_returns_all_active(self, client, seeded_db):
        resp = client.get("/api/intel/cards")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == len(_CARDS)
        assert data["covered_questions"] >= 12
        item = data["items"][0]
        for key in ("question_id", "title", "conclusion", "confidence", "sources"):
            assert key in item

    def test_questions_grouping(self, client, seeded_db):
        resp = client.get("/api/intel/cards/questions")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == len(_CARDS)
        qids = [g["question_id"] for g in data["groups"]]
        assert len(qids) == len(set(qids)), "分组出现重复问题"
        d4 = next(g for g in data["groups"] if g["question_id"] == "D4")
        assert d4["category"] == "evidence"

    def test_category_filter(self, client, seeded_db):
        resp = client.get("/api/intel/cards", params={"category": "evidence"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] > 0
        assert all(i["category"] == "evidence" for i in data["items"])

    def test_keyword_search(self, client, seeded_db):
        resp = client.get("/api/intel/cards", params={"q": "压分"})
        assert resp.status_code == 200
        assert resp.json()["total"] > 0


# ======================================================================
# B10 chat 注入（命中带源返回，不命中不硬塞）
# ======================================================================


class TestChatInjection:
    def test_detect_discrimination_question(self):
        intents = detect_data_intents("双非考复旦大学研究生复试会被歧视吗")
        assert any(i.domain == "intel_cards" for i in intents)

    def test_detect_advisor_contact_question(self):
        intents = detect_data_intents("复试前要提前联系导师吗")
        assert any(i.domain == "intel_cards" for i in intents)

    def test_no_intent_when_no_signal_words(self):
        intents = detect_data_intents("今天天气怎么样，推荐一部电影吧")
        assert not any(i.domain == "intel_cards" for i in intents)

    def test_run_search_injects_card_with_source(self, seeded_db):
        block, sources, has_hits = run_data_search(seeded_db, "双非考复旦大学会被歧视吗")
        assert has_hits
        assert "门道卡" in block
        assert "歧视" in block or "出身" in block
        assert any(s["url"].startswith("http") for s in sources)

    def test_run_search_miss_returns_honest_empty(self, seeded_db):
        block, sources, has_hits = run_data_search(seeded_db, "今天中午吃什么好")
        assert not has_hits
        assert sources == []

    def test_pure_school_name_does_not_trigger(self, seeded_db):
        # 纯校名（无门道主题词）不触发 intent——不命中不硬塞
        intents = detect_data_intents("复旦大学")
        assert not any(i.domain == "intel_cards" for i in intents)
