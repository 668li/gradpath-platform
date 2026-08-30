"""导师评价"负面可见性"钉子测试 — 防止未来排序改动埋掉低分/负面评价。

排序纪律（护城河「敢说真话」立场）：
- 评价列表一律按时间倒序，低分评价不得被点赞/评分排序沉底；
- 匿名投稿与实名评价同等展示（前端按 is_verified/reviewer_identity 分级标注）。
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.models.mentor import Mentor
from app.models.mentor_review import MentorReview
from app.services.mentor_service import get_mentor_reviews


def _make_review(mentor_id, *, overall: float, title: str, hours_ago: int) -> MentorReview:
    return MentorReview(
        mentor_id=mentor_id,
        user_id=uuid4(),
        rating_academic=round(overall),
        rating_guidance=round(overall),
        rating_relationship=round(overall),
        rating_funding=round(overall),
        rating_workload=round(overall),
        rating_career=round(overall),
        overall_rating=overall,
        title=title,
        content=f"{title}的内容",
        review_status="approved",
        # 排序键是 created_at（TimestampMixin 的 ORM default），必须显式拉开才能断言顺序
        created_at=datetime.now(timezone.utc) - timedelta(hours=hours_ago),
        submitted_at=(datetime.now(timezone.utc) - timedelta(hours=hours_ago)).isoformat(),
    )


@pytest.fixture
def seed_reviews_with_negative(db_session):
    """1 名导师 + 3 条评价：低分（最新）、高分（较旧）、低分（最旧）。"""
    mentor = Mentor(
        id=uuid4(),
        name="测试导师",
        university="测试大学",
        department="计算机学院",
        title="教授",
        avg_rating=3.0,
        review_count=3,
    )
    db_session.add(mentor)
    db_session.add_all(
        [
            _make_review(mentor.id, overall=2.0, title="低分但最新", hours_ago=1),
            _make_review(mentor.id, overall=5.0, title="高分较旧", hours_ago=24),
            _make_review(mentor.id, overall=1.0, title="低分最旧", hours_ago=720),
        ]
    )
    db_session.commit()
    return mentor.id


class TestNegativeReviewVisibility:
    def test_low_rating_reviews_not_buried(self, db_session, seed_reviews_with_negative):
        """低分评价按时间倒序正常出现在列表中，不会被评分排序埋没。"""
        reviews, total = get_mentor_reviews(db_session, seed_reviews_with_negative)
        assert total == 3
        titles = [r.title for r in reviews]
        assert "低分但最新" in titles and "低分最旧" in titles
        # 时间倒序：最新的低分评价排第一，而非高分评价
        assert reviews[0].title == "低分但最新"
        assert reviews[0].overall_rating == 2.0

    def test_ordering_is_created_at_not_rating(self, db_session, seed_reviews_with_negative):
        """排序键是时间而非评分：顺序与评分高低无关。"""
        reviews, _ = get_mentor_reviews(db_session, seed_reviews_with_negative)
        ratings_in_order = [r.overall_rating for r in reviews]
        # 若按评分排会得到 [5, 2, 1]；按时间排必须是 [2, 5, 1]
        assert ratings_in_order == [2.0, 5.0, 1.0]
