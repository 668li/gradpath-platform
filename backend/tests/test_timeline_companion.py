# tests/test_timeline_companion.py
"""流程伴随官 skill 测试 — 考试流程时间线的对话伴随面。

核心纪律（宪法 4 时间诚实）：OFFICIAL 才许断言、PREDICTED 只许试探句、
UNKNOWN=暂无可核验来源；本站不代办动作。夹具模式复用 test_exam_timeline_api
（seed 骨架 + apply_evidence_date 假 fetcher + derive_predicted_next_year）。
"""

from __future__ import annotations

import os
import sys
from datetime import date

# 确保 backend/app 在 path 中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import pytest

from app.models.exam_timeline import NodeStage
from app.services import timeline_service as tl
from app.services.data_search_service import detect_data_intents, run_data_search, search_timeline

_GOOD_BODY = (
    "<html><body>"
    "<p>中央机关及其直属机构2027年度考试录用公务员公告，根据公务员法和《公务员录用规定》组织实施。</p>"
    * 30
    + "<p>报考者可于2026年10月15日8:00至10月24日18:00期间登录专题网站进行报名并提交报考申请。</p></body></html>"
).encode()


def _fetch_ok(url):
    return 200, _GOOD_BODY


@pytest.fixture
def seeded(db_session):
    """零提案骨架：3 考次 ×12 节点全 UNKNOWN。"""
    from app.seed.seed_exam_timeline import seed_exam_timeline

    summary = seed_exam_timeline(db_session)
    assert summary["official_without_evidence"] == 0
    return db_session


def _set_2027_registration_official(db_session):
    """给 2027 报名节点过证据闸写 OFFICIAL（真 fetch 夹具，本地正文）。"""
    exams = {e.code: e for e in db_session.query(tl.Exam).all()}
    e27 = exams["guokao-2027"]
    reg27 = next(n for n in e27.nodes if n.stage_key == NodeStage.registration)
    tl.apply_evidence_date(
        db_session,
        reg27,
        on_date=date(2026, 10, 15),
        end_date=date(2026, 10, 24),
        source_url="https://www.gov.cn/x",
        fetcher=_fetch_ok,
    )
    db_session.commit()
    return reg27


# ======================================================================
# 意图与搜索器
# ======================================================================


class TestTimelineIntent:
    def test_intent_detected(self):
        intents = detect_data_intents("报名时间是什么时候")
        assert any(i.domain == "timeline" for i in intents)

    def test_intent_stage_and_track(self):
        intents = detect_data_intents("2027 国考到哪一步了，准考证什么时候打印")
        t = next(i for i in intents if i.domain == "timeline")
        assert t.params["track"] == "guokao"
        assert t.params["stage_key"] == "admission_ticket"

    def test_no_false_positive_on_career_chat(self):
        """「面试技巧/下一步职业规划」这类话不得劫持进时间线。"""
        assert not any(i.domain == "timeline" for i in detect_data_intents("帮我准备面试技巧"))
        assert not any(i.domain == "timeline" for i in detect_data_intents("我的职业下一步怎么走"))


class TestTimelineSearcher:
    def test_unknown_skeleton_honest_labels(self, seeded):
        hits = search_timeline(seeded)
        assert len(hits) == 12
        assert all("日期待定" in h.content for h in hits)
        assert all(h.source_table == "t_exam_node" for h in hits)

    def test_upcoming_exam_preferred(self, seeded):
        """默认选 upcoming 考次（2027 国考），closed 的 2026 不抢镜。"""
        hits = search_timeline(seeded)
        assert any(h.title.startswith("2027 国考") for h in hits)

    def test_stage_filter(self, seeded):
        hits = search_timeline(seeded, stage_key="registration")
        assert len(hits) == 1
        assert "报名" in hits[0].title

    def test_official_label_after_evidence(self, seeded):
        _set_2027_registration_official(seeded)
        hits = search_timeline(seeded, stage_key="registration")
        assert len(hits) == 1
        assert "官方：2026-10-15" in hits[0].content
        # 官方入口（考次专题）优先于证据源 URL——产品口径：用户去官方入口办事
        assert "bm.scs.gov.cn" in hits[0].url

    def test_track_filter(self, seeded):
        hits = search_timeline(seeded, track="shengkao")
        assert all(h.title.startswith("2026 广东省考") for h in hits)


# ======================================================================
# skill：inject_data / collect_sources / prompt 纪律
# ======================================================================


class TestTimelineCompanionSkill:
    def _skill(self):
        from app.skills.timeline_companion import TimelineCompanionSkill

        return TimelineCompanionSkill()

    def test_registered_and_active(self):
        from app.skills.registry import find_skill_instance, get_skill

        info = get_skill("timeline_companion")
        assert info is not None and info["is_active"] is True
        inst = find_skill_instance("2027 国考现在到哪一步了", {})
        assert inst is not None and inst.code == "timeline_companion"

    def test_inject_unknown_honest(self, seeded):
        skill = self._skill()
        assert skill.covered_data_domains == {"timeline"}
        out = skill.inject_data(seeded, "u1", "2027 国考到哪一步了")
        assert "2027 国考" in out
        assert "当前进度锚点" in out
        assert "日期待定" in out
        assert "2026 国考" not in out  # upcoming 考次优先，closed 不混入

    def test_inject_official_and_prediction(self, seeded):
        _set_2027_registration_official(seeded)
        out = self._skill().inject_data(seeded, "u1", "报名时间什么时候截止")
        assert "官方：2026-10-15~2026-10-24" in out
        assert "bm.scs.gov.cn" in out  # 官方入口行

    def test_empty_db_honest(self, db_session):
        out = self._skill().inject_data(db_session, "u1", "国考到哪一步")
        assert "暂无" in out and "禁止编造" in out

    def test_collect_sources_includes_official(self, seeded):
        _set_2027_registration_official(seeded)
        sources = self._skill().collect_sources(seeded, "u1", "报名时间")
        urls = [s["url"] for s in sources]
        assert any("bm.scs.gov.cn" in u for u in urls)  # 考次官方专题 + 节点官方入口

    def test_prompt_discipline(self):
        prompt = self._skill().build_system_prompt("用户：2027 国考", [])
        # 禁断言词表与提醒层同源（timeline_reminder.ASSERTIVE_WORDS）
        assert "明天" in prompt and "已发布" in prompt
        assert "公告后自动更新" in prompt
        assert "不代办" in prompt
        assert "禁止编造" in prompt


# ======================================================================
# chat 链路：域去重与诚实降级
# ======================================================================


class TestChatIntegration:
    def test_generic_layer_skips_skill_domain(self, seeded):
        block, sources, hits = run_data_search(
            seeded, "2027 国考报名时间什么时候截止", skip_domains={"timeline"}
        )
        assert block == "" and sources == [] and hits is False

    def test_generic_layer_serves_timeline_when_no_skill(self, seeded):
        block, sources, hits = run_data_search(seeded, "2027 国考报名时间什么时候截止")
        assert hits is True
        assert "t_exam_node" in block
        assert len(sources) >= 1
