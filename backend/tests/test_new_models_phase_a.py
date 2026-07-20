"""Phase A 模型建表验证测试 — 4 个新模型可正确创建表并执行 CRUD。"""
from datetime import date, datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import inspect

from app.models import (
    DarkKnowledgePushLog,
    DecisionReviewQueue,
    MemoryFactType,
    OnboardingStatus,
    PushFeedback,
    ReviewStatus,
    UserMemoryFact,
    UserOnboarding,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TestUserMemoryFactModel:
    """UserMemoryFact 模型测试"""

    def test_table_exists(self, db_session):
        """表应被正确创建"""
        insp = inspect(db_session.bind)
        assert "user_memory_facts" in insp.get_table_names()

    def test_create_memory_fact(self, db_session):
        """应能正确创建一条记忆事实"""
        user_id = uuid4()
        fact = UserMemoryFact(
            user_id=user_id,
            fact_type=MemoryFactType.preference,
            fact_key="preferred_industry",
            fact_value="金融科技",
            confidence=85,
            source="ai_extracted",
        )
        db_session.add(fact)
        db_session.commit()
        db_session.refresh(fact)

        assert fact.id is not None
        assert fact.fact_type == MemoryFactType.preference
        assert fact.fact_key == "preferred_industry"
        assert fact.fact_value == "金融科技"
        assert fact.confidence == 85
        assert fact.is_active is True
        assert fact.use_count == 0
        assert fact.user_feedback == "none"

    def test_memory_fact_type_enum_values(self):
        """枚举应包含 6 种类型"""
        types = {t.value for t in MemoryFactType}
        assert types == {
            "preference", "background", "goal",
            "constraint", "behavior", "fact"
        }


class TestUserOnboardingModel:
    """UserOnboarding 模型测试"""

    def test_table_exists(self, db_session):
        insp = inspect(db_session.bind)
        assert "user_onboardings" in insp.get_table_names()

    def test_create_onboarding(self, db_session):
        user_id = uuid4()
        ob = UserOnboarding(
            user_id=user_id,
            current_stage="大三",
            target_direction="postgrad",
            target_industry="互联网",
            self_assessment={"strengths": ["编程"], "weaknesses": ["英语"]},
        )
        db_session.add(ob)
        db_session.commit()
        db_session.refresh(ob)

        assert ob.id is not None
        assert ob.status == OnboardingStatus.in_progress
        assert ob.target_direction == "postgrad"
        assert ob.self_assessment["strengths"] == ["编程"]
        assert ob.recommended_path == {}
        assert ob.key_insights == []
        assert ob.completed_at is None
        assert ob.ai_diagnosis is None

    def test_complete_onboarding(self, db_session):
        """应能正确更新为已完成状态"""
        user_id = uuid4()
        ob = UserOnboarding(
            user_id=user_id,
            current_stage="大四",
            target_direction="employment",
            self_assessment={},
        )
        db_session.add(ob)
        db_session.commit()

        ob.status = OnboardingStatus.completed
        ob.ai_diagnosis = "建议优先准备实习"
        ob.recommended_path = {"short_term": ["找实习"]}
        ob.completed_at = _utcnow()
        db_session.commit()

        db_session.refresh(ob)
        assert ob.status == OnboardingStatus.completed
        assert ob.ai_diagnosis == "建议优先准备实习"
        assert ob.recommended_path["short_term"] == ["找实习"]
        assert ob.completed_at is not None


class TestDecisionReviewQueueModel:
    """DecisionReviewQueue 模型测试"""

    def test_table_exists(self, db_session):
        insp = inspect(db_session.bind)
        assert "decision_review_queue" in insp.get_table_names()

    def test_create_review_task(self, db_session):
        """应能正确创建回顾任务"""
        user_id = uuid4()
        decision_id = uuid4()
        review = DecisionReviewQueue(
            user_id=user_id,
            decision_id=decision_id,
            scheduled_at=date(2026, 8, 1),
            status=ReviewStatus.pending,
        )
        db_session.add(review)
        db_session.commit()
        db_session.refresh(review)

        assert review.id is not None
        assert review.status == ReviewStatus.pending
        assert review.scheduled_at == date(2026, 8, 1)
        assert review.ai_review_result == {}
        assert review.actual_outcome is None
        assert review.completed_at is None

    def test_complete_review(self, db_session):
        """应能正确更新为已完成状态"""
        user_id = uuid4()
        decision_id = uuid4()
        review = DecisionReviewQueue(
            user_id=user_id,
            decision_id=decision_id,
            scheduled_at=date(2026, 8, 1),
        )
        db_session.add(review)
        db_session.commit()

        review.status = ReviewStatus.completed
        review.actual_outcome = "成功上岸"
        review.satisfaction = 5
        review.ai_review_result = {
            "prediction_match": True,
            "accuracy_score": 90,
            "insights": ["决策方向正确"],
        }
        review.completed_at = _utcnow()
        db_session.commit()

        db_session.refresh(review)
        assert review.status == ReviewStatus.completed
        assert review.satisfaction == 5
        assert review.ai_review_result["accuracy_score"] == 90


class TestDarkKnowledgePushLogModel:
    """DarkKnowledgePushLog 模型测试"""

    def test_table_exists(self, db_session):
        insp = inspect(db_session.bind)
        assert "dark_knowledge_push_log" in insp.get_table_names()

    def test_create_push_log(self, db_session):
        """应能正确创建推送日志"""
        user_id = uuid4()
        dk_id = uuid4()
        log = DarkKnowledgePushLog(
            user_id=user_id,
            dark_knowledge_id=dk_id,
            stage="preparation",
            push_reason={"trigger": "decision_created"},
        )
        db_session.add(log)
        db_session.commit()
        db_session.refresh(log)

        assert log.id is not None
        assert log.feedback == PushFeedback.none
        assert log.pushed_at is not None
        assert log.read_at is None
        assert log.push_reason["trigger"] == "decision_created"
        assert log.stage == "preparation"

    def test_mark_read_with_feedback(self, db_session):
        """应能正确标记已读并记录反馈"""
        user_id = uuid4()
        dk_id = uuid4()
        log = DarkKnowledgePushLog(
            user_id=user_id,
            dark_knowledge_id=dk_id,
            stage="school_selection",
        )
        db_session.add(log)
        db_session.commit()

        log.read_at = _utcnow()
        log.feedback = PushFeedback.positive
        log.rating = 5
        db_session.commit()

        db_session.refresh(log)
        assert log.read_at is not None
        assert log.feedback == PushFeedback.positive
        assert log.rating == 5


class TestModelsRegistered:
    """验证 4 个新模型已正确注册到 app.models 命名空间"""

    def test_all_models_importable(self):
        from app.models import (
            DarkKnowledgePushLog,
            DecisionReviewQueue,
            UserMemoryFact,
            UserOnboarding,
        )
        assert UserMemoryFact is not None
        assert UserOnboarding is not None
        assert DecisionReviewQueue is not None
        assert DarkKnowledgePushLog is not None

    def test_all_enums_importable(self):
        from app.models import (
            MemoryFactType,
            OnboardingStatus,
            PushFeedback,
            ReviewStatus,
        )
        assert MemoryFactType is not None
        assert OnboardingStatus is not None
        assert ReviewStatus is not None
        assert PushFeedback is not None
