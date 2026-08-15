# backend/tests/test_kaoyan_news_api.py
"""考研资讯列表 API（Phase D1 扩展）测试 — 提纯字段/质量排序/筛选/分类。

覆盖：
- 默认列表：仅 approved，schema 含 5 个提纯字段
- sort=quality：quality_score 降序且 null 排最后（nullslast）
- quality_grade / source_platform / category / search 过滤
- /categories：去 general、按出现次数排序
- 非法 sort → 422；详情 404
"""
from hashlib import sha256

from sqlalchemy.orm import Session

from app.models.kaoyan_news import KaoyanNews


def _make_news(db: Session, **overrides) -> KaoyanNews:
    defaults = {
        "title": "某大学 2026 考研招生简章",
        "summary": "招生简章发布",
        "content": "2026 年硕士研究生招生简章内容。",
        "source_platform": "eol",
        "source_url": "",
        "status": "approved",
        "category": "招生简章",
        "quality_score": 60,
        "quality_grade": "B",
        "key_dates": [{"label": "报名", "date": "2025-10-15", "end_date": "2025-10-28"}],
        "is_expired": False,
        "ai_summary": None,
    }
    defaults.update(overrides)
    if not defaults["source_url"]:
        defaults["source_url"] = f"https://news.example.com/{sha256(defaults['title'].encode()).hexdigest()[:12]}"
    news = KaoyanNews(**defaults)
    db.add(news)
    db.commit()
    db.refresh(news)
    return news


class TestList:
    def test_default_list_returns_approved_with_purity_fields(self, client, db_session):
        _make_news(db_session, title="招生简章 A")
        _make_news(db_session, title="未过审资讯", status="pending", category="调剂")

        resp = client.get("/api/kaoyan-news")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        item = body["items"][0]
        # 5 个提纯字段齐全
        assert "ai_summary" in item
        assert item["quality_score"] == 60
        assert item["quality_grade"] == "B"
        assert item["key_dates"] == [
            {"label": "报名", "date": "2025-10-15", "end_date": "2025-10-28"}
        ]
        assert item["is_expired"] is False

    def test_sort_quality_desc_with_null_last(self, client, db_session):
        _make_news(db_session, title="高分资讯", quality_score=90, quality_grade="A")
        _make_news(db_session, title="中分资讯", quality_score=50, quality_grade="C")
        _make_news(db_session, title="历史无质量分", quality_score=None, quality_grade=None)

        resp = client.get("/api/kaoyan-news", params={"sort": "quality"})
        assert resp.status_code == 200
        titles = [i["title"] for i in resp.json()["items"]]
        assert titles == ["高分资讯", "中分资讯", "历史无质量分"]

    def test_quality_grade_filter(self, client, db_session):
        _make_news(db_session, title="A 级", quality_grade="A", quality_score=90)
        _make_news(db_session, title="B 级", quality_grade="B", quality_score=60)
        _make_news(db_session, title="B 级二", quality_grade="B", quality_score=55)

        resp = client.get("/api/kaoyan-news", params={"quality_grade": "B"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 2
        assert all(i["quality_grade"] == "B" for i in body["items"])

        # 小写入参归一化为大写
        resp_lower = client.get("/api/kaoyan-news", params={"quality_grade": "a"})
        assert resp_lower.json()["total"] == 1

    def test_source_platform_and_category_filter(self, client, db_session):
        _make_news(db_session, title="eol 源", source_platform="eol", category="调剂")
        _make_news(db_session, title="rss 源", source_platform="rss", category="调剂")
        _make_news(db_session, title="rss 复试", source_platform="rss", category="复试")

        by_platform = client.get("/api/kaoyan-news", params={"source_platform": "rss"})
        assert by_platform.json()["total"] == 2

        both = client.get(
            "/api/kaoyan-news",
            params={"source_platform": "rss", "category": "复试"},
        )
        assert both.json()["total"] == 1
        assert both.json()["items"][0]["title"] == "rss 复试"

    def test_search_matches_title(self, client, db_session):
        _make_news(db_session, title="2026 考研报名公告", category="政策")
        _make_news(db_session, title="某高校拟录取名单", category="复试")

        resp = client.get("/api/kaoyan-news", params={"search": "报名"})
        assert resp.json()["total"] == 1
        assert "报名" in resp.json()["items"][0]["title"]

    def test_invalid_sort_rejected(self, client):
        resp = client.get("/api/kaoyan-news", params={"sort": "bogus"})
        assert resp.status_code == 422

    def test_pagination(self, client, db_session):
        for i in range(5):
            _make_news(db_session, title=f"资讯 {i}")
        resp = client.get("/api/kaoyan-news", params={"page": 2, "page_size": 2})
        body = resp.json()
        assert body["total"] == 5
        assert body["page"] == 2
        assert len(body["items"]) == 2


class TestCategories:
    def test_categories_ordered_by_count_excludes_general(self, client, db_session):
        for _ in range(2):
            _make_news(db_session, title=f"调剂资讯 {sha256(str(_).encode()).hexdigest()[:6]}", category="调剂")
        _make_news(db_session, title="复试线公布", category="复试线")
        _make_news(db_session, title="未分类", category="general")
        _make_news(db_session, title="待审调剂", category="调剂", status="pending")

        resp = client.get("/api/kaoyan-news/categories")
        assert resp.status_code == 200
        # 调剂 2 条 > 复试线 1 条；general 与 pending 不出现
        assert resp.json()["categories"] == ["调剂", "复试线"]

    def test_categories_empty_when_no_approved(self, client, db_session):
        _make_news(db_session, title="待审", category="复试", status="pending")
        resp = client.get("/api/kaoyan-news/categories")
        assert resp.json()["categories"] == []


class TestDetail:
    def test_detail_returns_full_item(self, client, db_session):
        news = _make_news(db_session, title="详情页资讯")
        resp = client.get(f"/api/kaoyan-news/{news.id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == str(news.id)
        assert body["title"] == "详情页资讯"
        assert body["source_url"] == news.source_url

    def test_detail_404_for_missing(self, client):
        resp = client.get("/api/kaoyan-news/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 404
