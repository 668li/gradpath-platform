# tests/test_data_search_service.py
"""站内数据搜索层测试 — 三段式查库注入（docs/AI技能内置规划 V2）。

覆盖：参数抽取、代码级意图路由（置信不足不查库）、白名单搜索器溯源、
查无数据诚实降级、数据型 skill 的 inject_data 与域去重声明、registry 注册。
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
    extract_education,
    extract_major,
    extract_province,
    extract_schools,
    run_data_search,
    search_positions,
    search_school_intel,
    search_score_lines,
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

    def test_extract_education_province_dept(self):
        assert extract_education("本科生能报什么岗位") == "本科"
        assert extract_education("硕士研究生报岗") == "硕士"
        assert extract_province("广东的税务岗位多吗") == "广东"
        assert extract_dept("海关和国考税务哪个好") == "海关"
        assert extract_dept("随便看看") is None


# ======================================================================
# 代码级意图路由
# ======================================================================


class TestDetectIntents:
    def test_scoreline_with_school(self):
        intents = detect_data_intents("清华大学计算机专业分数线多少")
        assert intents[0].domain == "score_lines"
        assert intents[0].params["school"] == "清华大学"
        assert intents[0].params["major"] == "计算机"

    def test_insufficient_confidence_no_intent(self):
        """只说「分数线」无校名专业 → 不查库（诚实降级，绝不盲查）。"""
        assert detect_data_intents("分数线大概多少") == []

    def test_positions_intent(self):
        intents = detect_data_intents("本科学历在广东能报什么公务员职位")
        domains = [i.domain for i in intents]
        assert "positions" in domains
        pos = next(i for i in intents if i.domain == "positions")
        assert pos.params["education"] == "本科"
        assert pos.params["province"] == "广东"

    def test_positions_dept_major_collision_dropped(self):
        """「税务岗位」的税务是部门词不是专业词，同词时丢弃专业过滤（生产零命中事故回归）。"""
        pos = next(
            i for i in detect_data_intents("本科能报什么税务岗位") if i.domain == "positions"
        )
        assert pos.params["dept"] == "税务"
        assert pos.params["major"] is None

    def test_salary_intent(self):
        intents = detect_data_intents("计算机专业薪资怎么样")
        assert any(i.domain == "salary" for i in intents)


# ======================================================================
# 白名单搜索器（SQLite 内存库）
# ======================================================================


@pytest.fixture
def seed_user(db_session):
    from app.models.user import User

    user = User(email="ds-test@example.com", password_hash="x", name="测试")
    db_session.add(user)
    db_session.commit()
    return user


def _seed_scorelines(db_session):
    from app.models.grad_intel import GradScorelineRecord

    db_session.add_all(
        [
            GradScorelineRecord(
                university_name="清华大学",
                major_name="计算机科学与技术",
                year=2025,
                total_score_line=352,
                politics_score=60,
                foreign_language_score=60,
                business_1_score=90,
                business_2_score=90,
                enrollment_count=12,
                data_sources=[{"url": "https://yz.tsinghua.edu.cn/x"}],
            ),
            # 脏数据占位（total=0）必须被过滤
            GradScorelineRecord(
                university_name="清华大学",
                major_name="软件工程",
                year=2025,
                total_score_line=0,
                data_sources=[],
            ),
        ]
    )
    db_session.commit()


class TestSearchers:
    def test_score_lines_filters_dirty_and_attaches_source(self, db_session):
        _seed_scorelines(db_session)
        hits = search_score_lines(db_session, "清华大学", None)
        assert len(hits) == 1
        h = hits[0]
        assert "352" in h.content and "录取 12 人" in h.content
        assert h.url == "https://yz.tsinghua.edu.cn/x"
        assert h.year == 2025

    def test_score_lines_no_params_returns_empty(self, db_session):
        assert search_score_lines(db_session, None, None) == []

    def test_school_intel_chinese_mapping(self, db_session, seed_user):
        from app.models.grad_intel import GradSchoolIntel

        db_session.add(
            GradSchoolIntel(
                user_id=seed_user.id,
                school_name="清华大学",
                major_name="计算机科学与技术",
                school_tier="985",
                year=2026,
                background_discrimination="none",
                first_choice_protection="yes",
                admission_ratio="15:1",
                push_ratio="60%",
                actual_quota=8,
            )
        )
        db_session.commit()
        hits = search_school_intel(db_session, "清华")
        assert len(hits) == 1
        assert "报录比 15:1" in hits[0].content
        assert "卡第一学历: 不卡" in hits[0].content
        assert "保护一志愿: 是" in hits[0].content

    def test_positions_attaches_gwy_score_line(self, db_session):
        from app.models.gwy_position import GwyPosition
        from app.models.gwy_score_line import GwyScoreLine

        db_session.add_all(
            [
                GwyPosition(
                    id="p1", year=2026, exam_type="国考", position_code="0701263001",
                    dept_name="国家税务总局北京市税务局", position_name="基层岗",
                    education_req="仅限本科", major_req="计算机类", recruit_count=2,
                    work_location="北京",
                ),
                GwyScoreLine(
                    id="l1", year=2026, batch="首批", position_code="0701263001",
                    dept_name="国家税务总局北京市税务局", min_score=128.5,
                ),
                # 上一年职位不应出现
                GwyPosition(
                    id="p2", year=2025, exam_type="国考", position_code="0701263002",
                    dept_name="某海关", position_name="旧岗", education_req="仅限本科",
                    recruit_count=50,
                ),
            ]
        )
        db_session.commit()
        hits = search_positions(db_session, education="本科", dept="税务")
        assert len(hits) == 1
        assert "进面最低分 128.5" in hits[0].content
        assert "招 2 人" in hits[0].content


# ======================================================================
# run_data_search — 注入块与 sources
# ======================================================================


class TestRunDataSearch:
    def test_no_intent_returns_empty(self, db_session):
        block, sources, has_hits = run_data_search(db_session, "今天天气怎么样")
        assert block == "" and sources == [] and has_hits is False

    def test_intent_but_empty_honest_degradation(self, db_session):
        """检测到意图但库中无数据 → 明示禁编块。"""
        block, sources, has_hits = run_data_search(db_session, "复旦大学分数线多少")
        assert has_hits is False
        assert "禁止编造" in block
        assert sources == []

    def test_hits_block_contains_sources(self, db_session):
        _seed_scorelines(db_session)
        block, sources, has_hits = run_data_search(db_session, "清华大学计算机专业分数线多少")
        assert has_hits is True
        assert "站内数据检索结果" in block
        assert "grad_scoreline_records" in block
        assert len(sources) == 1
        assert sources[0]["type"] == "db"

    def test_skip_domains_dedup(self, db_session):
        """数据型 skill 已覆盖的域被跳过，不双注入。"""
        _seed_scorelines(db_session)
        block, _, _ = run_data_search(
            db_session, "清华大学计算机专业分数线多少", skip_domains={"score_lines", "school_intel"}
        )
        assert block == ""


# ======================================================================
# 数据型 skill 的 inject_data
# ======================================================================


class TestSkillInjectData:
    def test_grad_school_planning_injects_with_source(self, db_session):
        _seed_scorelines(db_session)
        from app.skills.grad_school_planning import GradSchoolPlanningSkill

        skill = GradSchoolPlanningSkill()
        assert skill.covered_data_domains >= {"score_lines"}
        out = skill.inject_data(db_session, "u1", "我想考清华大学计算机，稳吗")
        assert "352" in out
        assert "yz.tsinghua.edu.cn" in out

    def test_grad_school_planning_no_school_no_query(self, db_session):
        from app.skills.grad_school_planning import GradSchoolPlanningSkill

        assert GradSchoolPlanningSkill().inject_data(db_session, "u1", "帮我做考研规划") == ""

    def test_grad_school_planning_empty_honest(self, db_session):
        from app.skills.grad_school_planning import GradSchoolPlanningSkill

        out = GradSchoolPlanningSkill().inject_data(db_session, "u1", "复旦大学分数线多少")
        assert "暂无" in out and "禁止编造" in out

    def test_position_advisor_insufficient_asks_clarify(self, db_session):
        from app.skills.position_advisor import PositionAdvisorSkill

        out = PositionAdvisorSkill().inject_data(db_session, "u1", "帮我选个岗位")
        assert "澄清" in out

    def test_position_advisor_filters_positions(self, db_session):
        from app.models.gwy_position import GwyPosition
        from app.skills.position_advisor import PositionAdvisorSkill

        db_session.add(
            GwyPosition(
                id="p1", year=2026, exam_type="国考", position_code="0701263001",
                dept_name="国家税务总局北京市税务局", position_name="基层岗",
                education_req="仅限本科", major_req="计算机类", recruit_count=2,
                work_location="北京",
            )
        )
        db_session.commit()
        skill = PositionAdvisorSkill()
        assert skill.covered_data_domains == {"positions"}
        out = skill.inject_data(db_session, "u1", "本科计算机专业能报什么税务岗位")
        assert "税务" in out and "grad_scoreline_records" not in out

    def test_position_advisor_prompt_discipline(self):
        from app.skills.position_advisor import PositionAdvisorSkill

        prompt = PositionAdvisorSkill().build_system_prompt("用户：本科计算机", [])
        assert "禁止编造" in prompt or "绝不编造" in prompt
        assert "澄清" in prompt


# ======================================================================
# registry 注册与 dev skill 清理
# ======================================================================


class TestRegistry:
    def test_position_advisor_registered(self):
        from app.skills.registry import find_skill_instance, get_skill

        info = get_skill("position_advisor")
        assert info is not None and info["is_active"] is True
        inst = find_skill_instance("帮我选岗，国考有什么职位", {})
        assert inst is not None and inst.code == "position_advisor"

    def test_dev_skills_inactive(self):
        from app.skills.registry import list_skills

        dev_codes = [
            "api-endpoint-builder", "community-content-generator", "data-crawler-builder",
            "frontend-page-builder", "kaoyan-advisor", "seed-data-generator",
        ]
        by_code = {s["code"]: s for s in list_skills()}
        for code in dev_codes:
            assert by_code[code]["is_active"] is False, code

    def test_chat_skills_endpoint_filters_inactive(self, db_session):
        """GET /api/chat/skills 不再返回 dev-toolbox 死 skill。"""
        from fastapi.testclient import TestClient

        from app.core.deps import get_current_user
        from app.database import get_db
        from app.main import app

        app.dependency_overrides[get_db] = lambda: db_session
        app.dependency_overrides[get_current_user] = lambda: None
        try:
            client = TestClient(app)
            res = client.get("/api/chat/skills")
            assert res.status_code == 200
            codes = [s["code"] for s in res.json()]
            assert "position_advisor" in codes
            assert "api-endpoint-builder" not in codes
        finally:
            app.dependency_overrides.pop(get_db, None)
            app.dependency_overrides.pop(get_current_user, None)


# ======================================================================
# chat 契约
# ======================================================================


def test_send_message_response_accepts_agent_sources():
    from app.schemas.chat import SendMessageResponse

    resp = SendMessageResponse(
        content="基于真实数据的回答",
        skill_used="grad_school_planning",
        career_plan=None,
        agent_sources=[{"type": "db", "title": "清华大学 计算机 2025复试线", "url": "https://x"}],
        agent_confidence=0.7,
    )
    assert resp.agent_sources[0]["type"] == "db"
    # 兼容旧响应（无数据搜索时字段缺省）
    legacy = SendMessageResponse(content="a", skill_used="default", career_plan=None)
    assert legacy.agent_sources is None and legacy.agent_confidence is None
