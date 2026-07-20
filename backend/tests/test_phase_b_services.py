"""Phase B 服务层测试 — 覆盖 5 个新服务的核心功能。

测试策略：
- 不调用真实 LLM（mock AIService.chat）
- 使用 db_session fixture（SQLite 内存）
- 验证核心业务逻辑：CRUD、聚合、反馈、推送
"""
import asyncio
from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.models.dark_knowledge_push import DarkKnowledgePushLog, PushFeedback
from app.models.decision_review import DecisionReviewQueue, ReviewStatus
from app.models.destination_decision import DecisionStatus, DestinationDecision, DestinationType
from app.models.grad_intel import DarkKnowledge
from app.models.onboarding import OnboardingStatus, UserOnboarding
from app.models.user_memory import MemoryFactType, UserMemoryFact
from app.services.decision_pulse_service import (
    get_active_decisions,
    get_dark_knowledge_feed,
    get_full_pulse,
    get_memory_facts_panel,
    get_pulse_overview,
    get_review_queue,
)
from app.services.dark_knowledge_push_service import (
    get_push_history,
    get_unread_count,
    mark_read,
    push_for_decision,
    push_for_user,
    record_feedback,
)
from app.services.onboarding_service import (
    create_onboarding,
    generate_diagnosis,
    get_onboarding,
    is_onboarding_completed,
    skip_onboarding,
)
from app.services.user_context_service import (
    build_context_prompt,
    get_user_context,
)
from app.services.user_memory_service import (
    add_user_provided_fact,
    delete_memory_fact,
    extract_memory_facts,
    get_user_memory,
    update_memory_feedback,
)


# ========== user_context_service 测试 ==========

class TestUserContextService:
    def test_empty_user_context(self, db_session):
        """无任何数据时应返回空上下文"""
        ctx = get_user_context(db_session, uuid4())
        assert ctx["career_profile"] is None
        assert ctx["onboarding"] is None
        assert ctx["memory_facts"] == []
        assert ctx["recent_decisions"] == []
        assert ctx["recent_outcome_reports"] == []
        assert ctx["stats"]["total_decisions"] == 0
        assert ctx["stats"]["avg_decision_accuracy"] == 0.0

    def test_context_with_memory_facts(self, db_session):
        """有记忆事实时应聚合到上下文"""
        user_id = uuid4()
        fact = UserMemoryFact(
            user_id=user_id,
            fact_type=MemoryFactType.preference,
            fact_key="preferred_industry",
            fact_value="金融",
            confidence=90,
        )
        db_session.add(fact)
        db_session.commit()

        ctx = get_user_context(db_session, user_id)
        assert len(ctx["memory_facts"]) == 1
        assert ctx["memory_facts"][0]["fact_key"] == "preferred_industry"
        assert ctx["stats"]["memory_count"] == 1

    def test_context_excludes_inactive_facts(self, db_session):
        """is_active=False 的事实不应出现在上下文"""
        user_id = uuid4()
        db_session.add_all([
            UserMemoryFact(
                user_id=user_id,
                fact_type=MemoryFactType.background,
                fact_key="gpa",
                fact_value="3.8",
                confidence=90,
                is_active=True,
            ),
            UserMemoryFact(
                user_id=user_id,
                fact_type=MemoryFactType.background,
                fact_key="old_gpa",
                fact_value="3.5",
                confidence=50,
                is_active=False,
            ),
        ])
        db_session.commit()

        ctx = get_user_context(db_session, user_id)
        assert len(ctx["memory_facts"]) == 1
        assert ctx["memory_facts"][0]["fact_key"] == "gpa"

    def test_build_context_prompt_empty(self, db_session):
        """无数据时应返回统计为 0 的上下文"""
        prompt = build_context_prompt(db_session, uuid4())
        # 无数据时 stats 部分仍会显示（值为 0），但不包含画像/记忆等
        assert "共 0 个决策" in prompt
        assert "AI 记忆 0 条" in prompt

    def test_build_context_prompt_with_data(self, db_session):
        """有数据时应包含画像信息"""
        user_id = uuid4()
        db_session.add(UserMemoryFact(
            user_id=user_id,
            fact_type=MemoryFactType.preference,
            fact_key="preferred_industry",
            fact_value="金融科技",
            confidence=95,
        ))
        db_session.commit()

        prompt = build_context_prompt(db_session, user_id)
        assert "preferred_industry=金融科技" in prompt
        assert "置信度95" in prompt


# ========== user_memory_service 测试 ==========

class TestUserMemoryService:
    def test_get_user_memory_empty(self, db_session):
        """无记忆时应返回空列表"""
        facts = get_user_memory(db_session, uuid4())
        assert facts == []

    def test_get_user_memory_with_filter(self, db_session):
        """按 fact_type 过滤"""
        user_id = uuid4()
        db_session.add_all([
            UserMemoryFact(
                user_id=user_id,
                fact_type=MemoryFactType.preference,
                fact_key="industry",
                fact_value="金融",
                confidence=90,
            ),
            UserMemoryFact(
                user_id=user_id,
                fact_type=MemoryFactType.background,
                fact_key="gpa",
                fact_value="3.8",
                confidence=80,
            ),
        ])
        db_session.commit()

        # 不带过滤
        all_facts = get_user_memory(db_session, user_id)
        assert len(all_facts) == 2

        # 按 preference 过滤
        pref_facts = get_user_memory(db_session, user_id, fact_type=MemoryFactType.preference)
        assert len(pref_facts) == 1
        assert pref_facts[0].fact_key == "industry"

    def test_update_memory_feedback_positive(self, db_session):
        """positive 反馈应提升置信度"""
        user_id = uuid4()
        fact = UserMemoryFact(
            user_id=user_id,
            fact_type=MemoryFactType.preference,
            fact_key="industry",
            fact_value="金融",
            confidence=70,
        )
        db_session.add(fact)
        db_session.commit()

        updated = update_memory_feedback(db_session, user_id, fact.id, "positive")
        assert updated.confidence == 80
        assert updated.user_feedback == "positive"

    def test_update_memory_feedback_negative_disables(self, db_session):
        """confidence 低于 20 时应停用"""
        user_id = uuid4()
        fact = UserMemoryFact(
            user_id=user_id,
            fact_type=MemoryFactType.preference,
            fact_key="industry",
            fact_value="金融",
            confidence=15,
        )
        db_session.add(fact)
        db_session.commit()

        updated = update_memory_feedback(db_session, user_id, fact.id, "negative")
        assert updated.confidence == 0
        assert updated.is_active is False

    def test_add_user_provided_fact_overrides_existing(self, db_session):
        """用户主动告知应覆盖同 key 的旧事实"""
        user_id = uuid4()
        old = UserMemoryFact(
            user_id=user_id,
            fact_type=MemoryFactType.background,
            fact_key="gpa",
            fact_value="3.5",
            confidence=70,
            source="ai_extracted",
        )
        db_session.add(old)
        db_session.commit()

        new = add_user_provided_fact(
            db_session, user_id, MemoryFactType.background, "gpa", "3.9"
        )
        assert new.confidence == 100
        assert new.source == "user_provided"

        # 旧事实应被置为 inactive
        db_session.refresh(old)
        assert old.is_active is False

    def test_delete_memory_fact(self, db_session):
        """删除应软删除"""
        user_id = uuid4()
        fact = UserMemoryFact(
            user_id=user_id,
            fact_type=MemoryFactType.fact,
            fact_key="test",
            fact_value="value",
        )
        db_session.add(fact)
        db_session.commit()

        assert delete_memory_fact(db_session, user_id, fact.id) is True
        db_session.refresh(fact)
        assert fact.is_active is False

    def test_extract_memory_facts_empty_messages(self, db_session):
        """空消息列表应直接返回空"""
        result = asyncio.run(extract_memory_facts(db_session, uuid4(), None, []))
        assert result == []

    @patch("app.services.user_memory_service.AIService")
    def test_extract_memory_facts_with_mock_llm(self, mock_ai_cls, db_session):
        """mock LLM 返回 JSON 数组，应正确抽取并存储"""
        user_id = uuid4()
        mock_ai = MagicMock()
        mock_ai.chat = AsyncMock(return_value='''[
            {"fact_type": "preference", "fact_key": "preferred_industry", "fact_value": "金融科技", "confidence": 95},
            {"fact_type": "background", "fact_key": "gpa", "fact_value": "3.8", "confidence": 90}
        ]''')
        mock_ai_cls.return_value = mock_ai

        messages = [
            {"role": "user", "content": "我GPA 3.8，想去金融科技行业"},
            {"role": "assistant", "content": "好的，金融科技..."},
        ]
        result = asyncio.run(extract_memory_facts(db_session, user_id, None, messages))

        assert len(result) == 2
        assert result[0].fact_key == "preferred_industry"
        assert result[0].fact_value == "金融科技"
        assert result[0].confidence == 95
        assert result[0].source == "ai_extracted"

    @patch("app.services.user_memory_service.AIService")
    def test_extract_memory_facts_overwrites_same_key(self, mock_ai_cls, db_session):
        """同 fact_key 的新事实应覆盖旧事实"""
        user_id = uuid4()
        # 旧事实
        db_session.add(UserMemoryFact(
            user_id=user_id,
            fact_type=MemoryFactType.background,
            fact_key="gpa",
            fact_value="3.5",
            confidence=70,
        ))
        db_session.commit()

        mock_ai = MagicMock()
        mock_ai.chat = AsyncMock(return_value='''[
            {"fact_type": "background", "fact_key": "gpa", "fact_value": "3.9", "confidence": 95}
        ]''')
        mock_ai_cls.return_value = mock_ai

        messages = [{"role": "user", "content": "我GPA其实是3.9"}]
        result = asyncio.run(extract_memory_facts(db_session, user_id, None, messages))

        assert len(result) == 1
        assert result[0].fact_value == "3.9"

        # 旧事实应被置为 inactive
        active_facts = get_user_memory(db_session, user_id)
        assert len(active_facts) == 1
        assert active_facts[0].fact_value == "3.9"


# ========== onboarding_service 测试 ==========

class TestOnboardingService:
    def test_create_onboarding_new(self, db_session):
        """新建 onboarding"""
        user_id = uuid4()
        ob = create_onboarding(
            db_session,
            user_id,
            current_stage="大三",
            target_direction="postgrad",
            target_industry="互联网",
            self_assessment={"strengths": ["编程"], "weaknesses": ["英语"]},
        )
        assert ob.id is not None
        assert ob.status == OnboardingStatus.in_progress
        assert ob.target_direction == "postgrad"
        assert ob.self_assessment["strengths"] == ["编程"]

    def test_create_onboarding_updates_existing(self, db_session):
        """已有 onboarding 时应更新而非新建"""
        user_id = uuid4()
        ob1 = create_onboarding(
            db_session, user_id, "大三", "postgrad", "互联网", {"a": 1}
        )
        ob2 = create_onboarding(
            db_session, user_id, "大四", "employment", "金融", {"b": 2}
        )
        assert ob1.id == ob2.id
        assert ob2.current_stage == "大四"
        assert ob2.target_direction == "employment"

    def test_is_onboarding_completed(self, db_session):
        """完成状态判断"""
        user_id = uuid4()
        assert is_onboarding_completed(db_session, user_id) is False

        ob = create_onboarding(db_session, user_id, "大三", "postgrad", None, {})
        assert is_onboarding_completed(db_session, user_id) is False

        ob.status = OnboardingStatus.completed
        db_session.commit()
        assert is_onboarding_completed(db_session, user_id) is True

    def test_skip_onboarding_creates_record(self, db_session):
        """跳过时应创建 skipped 记录"""
        user_id = uuid4()
        ob = skip_onboarding(db_session, user_id)
        assert ob.status == OnboardingStatus.skipped
        assert is_onboarding_completed(db_session, user_id) is False

    def test_get_onboarding_returns_latest(self, db_session):
        """应返回最新的 onboarding"""
        user_id = uuid4()
        # 显式设置不同的 created_at，避免 SQLite 时间戳精度问题
        old_time = datetime.now(timezone.utc) - timedelta(hours=1)
        new_time = datetime.now(timezone.utc)

        ob1 = UserOnboarding(
            user_id=user_id,
            current_stage="大一",
            target_direction="postgrad",
            self_assessment={},
            created_at=old_time,
        )
        db_session.add(ob1)
        db_session.commit()

        ob2 = UserOnboarding(
            user_id=user_id,
            current_stage="大三",
            target_direction="employment",
            self_assessment={},
            created_at=new_time,
        )
        db_session.add(ob2)
        db_session.commit()

        latest = get_onboarding(db_session, user_id)
        assert latest.id == ob2.id

    @patch("app.services.onboarding_service.AIService")
    def test_generate_diagnosis_success(self, mock_ai_cls, db_session):
        """mock LLM 返回诊断 JSON"""
        user_id = uuid4()
        ob = create_onboarding(db_session, user_id, "大三", "postgrad", "互联网", {})

        mock_ai = MagicMock()
        mock_ai.chat = AsyncMock(return_value='''{
            "diagnosis": "用户具备较强技术背景，建议优先准备考研",
            "recommended_path": {
                "short_term": ["选学校", "买资料"],
                "mid_term": ["系统复习"],
                "long_term": ["考研上岸"]
            },
            "key_insights": [
                {"type": "strength", "text": "技术能力强"},
                {"type": "risk", "text": "英语偏弱"}
            ]
        }''')
        mock_ai_cls.return_value = mock_ai

        result = asyncio.run(generate_diagnosis(db_session, ob.id))
        assert result.status == OnboardingStatus.completed
        assert result.completed_at is not None
        assert "技术背景" in result.ai_diagnosis
        assert len(result.recommended_path["short_term"]) == 2
        assert len(result.key_insights) == 2

    @patch("app.services.onboarding_service.AIService")
    def test_generate_diagnosis_invalid_json_fallback(self, mock_ai_cls, db_session):
        """LLM 返回非 JSON 时应兜底处理"""
        user_id = uuid4()
        ob = create_onboarding(db_session, user_id, "大三", "postgrad", None, {})

        mock_ai = MagicMock()
        mock_ai.chat = AsyncMock(return_value="这是一段非 JSON 的诊断文本")
        mock_ai_cls.return_value = mock_ai

        result = asyncio.run(generate_diagnosis(db_session, ob.id))
        assert result.status == OnboardingStatus.completed
        assert "非 JSON" in result.ai_diagnosis
        assert result.recommended_path == {}


# ========== decision_pulse_service 测试 ==========

class TestDecisionPulseService:
    def test_pulse_overview_empty(self, db_session):
        """无数据时应返回零值"""
        overview = get_pulse_overview(db_session, uuid4())
        assert overview["total_decisions"] == 0
        assert overview["completed_reviews"] == 0
        assert overview["pending_reviews"] == 0
        assert overview["memory_count"] == 0
        assert overview["due_reviews"] == 0
        assert overview["unread_pushes"] == 0
        assert overview["active_decisions"] == 0

    def test_pulse_overview_with_data(self, db_session):
        """有数据时应正确统计"""
        user_id = uuid4()
        # 1 个进行中决策
        db_session.add(DestinationDecision(
            user_id=user_id,
            decision_date=date.today(),
            destination_type=DestinationType.postgrad,
            status=DecisionStatus.planned,
            confidence=4,
            details={},
        ))
        # 1 个待回顾任务（已到期）
        db_session.add(DecisionReviewQueue(
            user_id=user_id,
            decision_id=uuid4(),
            scheduled_at=date.today() - timedelta(days=1),
            status=ReviewStatus.pending,
        ))
        # 1 个未读推送
        db_session.add(DarkKnowledgePushLog(
            user_id=user_id,
            dark_knowledge_id=uuid4(),
            stage="decision",
        ))
        # 1 条记忆事实
        db_session.add(UserMemoryFact(
            user_id=user_id,
            fact_type=MemoryFactType.fact,
            fact_key="test",
            fact_value="value",
        ))
        db_session.commit()

        overview = get_pulse_overview(db_session, user_id)
        assert overview["total_decisions"] == 1
        assert overview["active_decisions"] == 1
        assert overview["due_reviews"] == 1
        assert overview["unread_pushes"] == 1
        assert overview["memory_count"] == 1

    def test_get_active_decisions(self, db_session):
        """进行中决策列表"""
        user_id = uuid4()
        db_session.add_all([
            DestinationDecision(
                user_id=user_id,
                decision_date=date.today(),
                destination_type=DestinationType.postgrad,
                status=DecisionStatus.planned,
                confidence=4,
                details={},
            ),
            DestinationDecision(
                user_id=user_id,
                decision_date=date.today(),
                destination_type=DestinationType.employment,
                status=DecisionStatus.executed,
                confidence=5,
                details={},
            ),
        ])
        db_session.commit()

        active = get_active_decisions(db_session, user_id)
        assert len(active) == 1
        assert active[0]["destination_type"] == "postgrad"

    def test_get_review_queue_overdue(self, db_session):
        """过期回顾任务应标记 is_overdue"""
        user_id = uuid4()
        db_session.add(DecisionReviewQueue(
            user_id=user_id,
            decision_id=uuid4(),
            scheduled_at=date.today() - timedelta(days=5),
            status=ReviewStatus.pending,
        ))
        db_session.commit()

        queue = get_review_queue(db_session, user_id)
        assert len(queue) == 1
        assert queue[0]["is_overdue"] is True
        assert queue[0]["days_until_due"] < 0

    def test_get_dark_knowledge_feed(self, db_session):
        """暗知识推送流"""
        user_id = uuid4()
        dk_id = uuid4()
        db_session.add(DarkKnowledge(
            stage="decision",
            category="测试",
            title="测试暗知识",
            content="这是测试内容",
            importance="high",
        ))
        db_session.commit()
        # 需要获取 dk.id
        dk = db_session.query(DarkKnowledge).filter(DarkKnowledge.title == "测试暗知识").first()
        db_session.add(DarkKnowledgePushLog(
            user_id=user_id,
            dark_knowledge_id=dk.id,
            stage="decision",
        ))
        db_session.commit()

        feed = get_dark_knowledge_feed(db_session, user_id)
        assert len(feed) == 1
        assert feed[0]["title"] == "测试暗知识"
        assert feed[0]["is_read"] is False

    def test_get_full_pulse(self, db_session):
        """完整看板数据应包含所有面板"""
        pulse = get_full_pulse(db_session, uuid4())
        assert "overview" in pulse
        assert "active_decisions" in pulse
        assert "review_queue" in pulse
        assert "dark_knowledge_feed" in pulse
        assert "memory_facts" in pulse


# ========== dark_knowledge_push_service 测试 ==========

class TestDarkKnowledgePushService:
    def test_push_for_user_no_candidates(self, db_session):
        """无候选暗知识时应返回空"""
        result = push_for_user(db_session, uuid4(), stage="decision", limit=3)
        assert result == []

    def test_push_for_user_creates_logs(self, db_session):
        """应创建推送日志"""
        user_id = uuid4()
        # 创建 3 条暗知识
        for i in range(3):
            db_session.add(DarkKnowledge(
                stage="decision",
                category=f"分类{i}",
                title=f"标题{i}",
                content=f"内容{i}",
                importance="high",
                sort_order=i,
            ))
        db_session.commit()

        result = push_for_user(db_session, user_id, stage="decision", limit=2)
        assert len(result) == 2

    def test_push_for_user_dedup(self, db_session):
        """同一条暗知识不应重复推送"""
        user_id = uuid4()
        dk = DarkKnowledge(
            stage="decision",
            category="测试",
            title="唯一测试",
            content="内容",
            importance="high",
        )
        db_session.add(dk)
        db_session.commit()

        # 第一次推送
        r1 = push_for_user(db_session, user_id, stage="decision", limit=5)
        assert len(r1) == 1

        # 第二次推送（应该没有新的候选）
        r2 = push_for_user(db_session, user_id, stage="decision", limit=5)
        assert len(r2) == 0

    def test_push_for_decision(self, db_session):
        """决策触发推送"""
        user_id = uuid4()
        decision_id = uuid4()
        db_session.add(DarkKnowledge(
            stage="decision",
            category="决策相关",
            title="决策必知",
            content="内容",
            importance="high",
        ))
        db_session.commit()

        result = push_for_decision(
            db_session, user_id, decision_id, "postgrad", limit=2
        )
        assert len(result) == 1
        assert result[0].push_reason["trigger"] == "decision_created"
        assert result[0].push_reason["decision_id"] == str(decision_id)

    def test_mark_read(self, db_session):
        """标记已读"""
        user_id = uuid4()
        log = DarkKnowledgePushLog(
            user_id=user_id,
            dark_knowledge_id=uuid4(),
            stage="decision",
        )
        db_session.add(log)
        db_session.commit()

        result = mark_read(db_session, user_id, log.id)
        assert result.read_at is not None

        # 重复标记不应报错
        result2 = mark_read(db_session, user_id, log.id)
        assert result2.read_at == result.read_at

    def test_record_feedback(self, db_session):
        """记录反馈"""
        user_id = uuid4()
        log = DarkKnowledgePushLog(
            user_id=user_id,
            dark_knowledge_id=uuid4(),
            stage="decision",
        )
        db_session.add(log)
        db_session.commit()

        result = record_feedback(
            db_session,
            user_id,
            log.id,
            PushFeedback.positive,
            rating=5,
            notes="很有用",
        )
        assert result.feedback == PushFeedback.positive
        assert result.rating == 5
        assert result.feedback_notes == "很有用"
        assert result.read_at is not None  # 反馈时自动标记已读

    def test_get_unread_count(self, db_session):
        """未读数统计"""
        user_id = uuid4()
        db_session.add_all([
            DarkKnowledgePushLog(
                user_id=user_id,
                dark_knowledge_id=uuid4(),
                stage="decision",
            ),
            DarkKnowledgePushLog(
                user_id=user_id,
                dark_knowledge_id=uuid4(),
                stage="preparation",
                read_at=datetime.now(timezone.utc),
            ),
        ])
        db_session.commit()

        assert get_unread_count(db_session, user_id) == 1

    def test_get_push_history_only_unread(self, db_session):
        """只看未读"""
        user_id = uuid4()
        db_session.add_all([
            DarkKnowledgePushLog(
                user_id=user_id,
                dark_knowledge_id=uuid4(),
                stage="decision",
            ),
            DarkKnowledgePushLog(
                user_id=user_id,
                dark_knowledge_id=uuid4(),
                stage="preparation",
                read_at=datetime.now(timezone.utc),
            ),
        ])
        db_session.commit()

        history = get_push_history(db_session, user_id, only_unread=True)
        assert len(history) == 1
        assert history[0].stage == "decision"
