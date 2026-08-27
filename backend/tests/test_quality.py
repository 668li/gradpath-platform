# backend/tests/test_quality.py
"""资讯质量分级（Phase A2）单元测试 — 权威度/时效/完整度/可溯源 → 0-100 + A/B/C/D。

覆盖：
- 官方域名（edu.cn）权威度 40；门户（sina/eol）25；社区 15；其他 10
- 时效衰减：24h 内满分 30 → 180 天后 0
- 完整度：长正文 20 分 + 摘要加分
- 可溯源：有合法 source_url 才 +10
- 分级阈值边界：75/55/35 → A/B/C，34 → D
"""

from datetime import datetime, timedelta, timezone

from app.crawlers.research.quality import (
    _completeness_score,
    _freshness_score,
    grade_of,
    score_item,
)


def _utc_ago(hours: float) -> datetime:
    return datetime.now(timezone.utc) - timedelta(hours=hours)


class TestScoreItem:
    def test_official_news_scores_a(self):
        # 官方域名 + 24h 内 + 长正文（>=1000 字拿满完整度）+ 合法 URL → 40+30+20+10 = 100 → A
        score, grade = score_item(
            title="某大学 2026 考研招生简章",
            content="长正文" * 400,
            summary="招生简章发布",
            source_url="https://yz.xx.edu.cn/notice/2026/1.html",
            published_at=_utc_ago(1),
        )
        assert score == 100
        assert grade == "A"

    def test_portal_source_scores_a(self):
        # 门户教育频道 25 + 时效 30 + 完整 20 + 溯源 10 = 85 → A
        score, grade = score_item(
            title="2026 考研报名时间公布",
            content="正文内容" * 400,
            summary="摘要",
            source_url="https://kaoyan.eol.cn/news.shtml",
            published_at=_utc_ago(2),
        )
        assert score == 85
        assert grade == "A"

    def test_no_source_url_loses_traceability(self):
        # 无 source_url：无法判定权威度（0）+ 溯源 0 → 40 → C
        score, grade = score_item(
            title="标题",
            content="正文" * 100,
            source_url="",
            published_at=_utc_ago(1),
        )
        assert score == 40
        assert grade == "C"

    def test_old_stale_news_drops_score(self):
        # 180 天前 → 时效 0；门户 25 + 完整 20 + 溯源 10 = 55 → B
        score, grade = score_item(
            title="旧闻",
            content="正文" * 500,
            source_url="https://sina.com.cn/edu/kaoyan.xml",
            published_at=_utc_ago(200 * 24),
        )
        assert score == 55
        assert grade == "B"

    def test_empty_content_and_unknown_time_scores_d(self):
        # 无正文（完整 0）+ 未知时间（时效 0）+ 其他域 10 + 溯源 10 = 20 → D
        score, grade = score_item(
            title="只有标题",
            source_url="https://some-blog.example.com/p",
            published_at=None,
            crawled_at=None,
        )
        assert score == 20
        assert grade == "D"


class TestFreshness:
    def test_fresh_full_marks(self):
        assert _freshness_score(_utc_ago(0.5), None) == 30

    def test_decays_over_time(self):
        assert _freshness_score(_utc_ago(3 * 24), None) == 25  # <7d
        assert _freshness_score(_utc_ago(15 * 24), None) == 18  # <30d
        assert _freshness_score(_utc_ago(60 * 24), None) == 10  # <90d
        assert _freshness_score(_utc_ago(120 * 24), None) == 5  # <180d
        assert _freshness_score(_utc_ago(200 * 24), None) == 0  # >=180d

    def test_unknown_time_neutral(self):
        assert _freshness_score(None, None) == 0

    def test_uses_crawled_at_when_published_missing(self):
        assert _freshness_score(None, _utc_ago(1)) == 30


class TestCompleteness:
    def test_long_content_full_marks(self):
        assert _completeness_score("x" * 1200, "") == 20

    def test_medium_content_tier(self):
        assert _completeness_score("x" * 600, "") == 15
        assert _completeness_score("x" * 150, "") == 10

    def test_summary_bonus_capped(self):
        assert _completeness_score("x" * 600, "有摘要") == 17
        # 长正文已满分时摘要不叠加
        assert _completeness_score("x" * 1200, "有摘要") == 20

    def test_empty_content_zero(self):
        assert _completeness_score("", "") == 0


class TestGradeThresholds:
    def test_boundaries(self):
        assert grade_of(75) == "A"
        assert grade_of(74) == "B"
        assert grade_of(55) == "B"
        assert grade_of(54) == "C"
        assert grade_of(35) == "C"
        assert grade_of(34) == "D"

    def test_extremes(self):
        assert grade_of(100) == "A"
        assert grade_of(0) == "D"
