# backend/tests/test_cursor_pagination.py
"""C5 游标分页测试 — 覆盖工具函数 + 3 个 cursor 端点。

测试范围：
1. app.core.cursor_pagination 工具函数
   - encode_cursor / decode_cursor 往返一致性
   - decode_cursor 对无效输入返回 None
   - apply_cursor_filter 在 descending=True 时生成正确的 WHERE 子句
2. GET /api/posts/public/cursor — 多页翻页 / topic_type 过滤 / 空结果 / 无效 cursor
3. GET /api/mentors/kaoyan-mentors/cursor — university 过滤 / min_rating 过滤 / 分页
4. GET /api/employment/schools/cursor — 仅返回有 published 报告的 school / 排除 pending / 分页
"""
from datetime import date, timezone
from uuid import uuid4

import pytest

from app.core.cursor_pagination import apply_cursor_filter, decode_cursor, encode_cursor
from app.models.mentor import Mentor
from app.models.notification import Notification  # noqa: F401 — 确保 ORM 元数据加载
from app.models.post import Post, PostTopicType
from app.models.report_record import ParseStatus, ReportRecord
from app.models.school import School
from app.models.user import User


# ======================================================================
# 工具函数测试
# ======================================================================

class TestCursorPaginationUtils:
    """encode_cursor / decode_cursor / apply_cursor_filter 单元测试。"""

    def test_encode_decode_roundtrip(self):
        """encode → decode 应保持 (ts, id) 一致。"""
        ts = "2026-07-20T10:00:00+00:00"
        item_id = "post-123"
        cursor = encode_cursor(ts, item_id)
        decoded = decode_cursor(cursor)
        assert decoded is not None
        assert decoded["ts"] == ts
        assert decoded["id"] == item_id

    def test_encode_decode_with_uuid(self):
        """encode → decode 应正确处理 UUID 字符串。"""
        ts = "2026-07-20T10:00:00+00:00"
        item_id = str(uuid4())
        cursor = encode_cursor(ts, item_id)
        decoded = decode_cursor(cursor)
        assert decoded is not None
        assert decoded["id"] == item_id

    def test_decode_invalid_cursor_returns_none(self):
        """decode 对无效字符串应返回 None，不抛异常。"""
        assert decode_cursor("not-a-valid-cursor") is None
        assert decode_cursor("") is None
        assert decode_cursor("!!!") is None
        # 非 base64 内容
        assert decode_cursor("@@@@") is None

    def test_apply_cursor_filter_descending(self, db_session):
        """descending=True 时游标应排除游标记录本身及其后的记录。

        构造 3 条 created_at 严格递减的 Post（手动设置时间，避免微秒级时间相同
        导致 UUID 子句成为唯一判定条件）。
        """
        from datetime import datetime, timedelta
        base_ts = datetime(2026, 7, 20, 10, 0, 0, tzinfo=timezone.utc)
        posts = []
        for i in range(3):
            p = Post(
                topic_type=PostTopicType.school_major,
                topic_key=f"test-{i}",
                content=f"content-{i}",
                user_id=uuid4(),
            )
            # 显式设置 created_at 为严格递减，模拟默认按时间倒序
            p.created_at = base_ts - timedelta(seconds=i)
            db_session.add(p)
            posts.append(p)
        db_session.commit()

        # 取第 1 条（时间最新）作为游标 → descending=True 时
        # 应返回 created_at < cursor_ts 的记录（即第 2、3 条）
        cursor_post = posts[0]
        cursor = encode_cursor(
            cursor_post.created_at.isoformat(), str(cursor_post.id)
        )
        query = db_session.query(Post)
        filtered = apply_cursor_filter(
            query, cursor,
            time_col=Post.created_at, id_col=Post.id,
            descending=True,
        )
        results = filtered.all()
        result_ids = {str(r.id) for r in results}
        # 游标记录本身不应出现
        assert str(cursor_post.id) not in result_ids
        # 应返回剩下的 2 条
        assert len(results) == 2
        # 且这 2 条的 created_at 都应严格小于游标的 created_at
        for r in results:
            assert r.created_at < cursor_post.created_at

    def test_apply_cursor_filter_no_cursor_returns_all(self, db_session):
        """cursor=None 时不应追加任何过滤条件，返回全部记录。"""
        for i in range(2):
            db_session.add(Post(
                topic_type=PostTopicType.school_major,
                topic_key=f"no-cursor-{i}",
                content=f"c-{i}",
                user_id=uuid4(),
            ))
        db_session.commit()

        query = db_session.query(Post)
        filtered = apply_cursor_filter(
            query, None,
            time_col=Post.created_at, id_col=Post.id,
        )
        assert filtered.count() == 2

    def test_apply_cursor_filter_invalid_cursor_returns_all(self, db_session):
        """无效 cursor 应被忽略（不追加过滤条件）。"""
        for i in range(2):
            db_session.add(Post(
                topic_type=PostTopicType.school_major,
                topic_key=f"invalid-{i}",
                content=f"c-{i}",
                user_id=uuid4(),
            ))
        db_session.commit()

        query = db_session.query(Post)
        filtered = apply_cursor_filter(
            query, "not-a-valid-cursor",
            time_col=Post.created_at, id_col=Post.id,
        )
        # 无效 cursor → decode 返回 None → apply_cursor_filter 返回原 query
        assert filtered.count() == 2


# ======================================================================
# GET /api/posts/public/cursor
# ======================================================================

class TestPostsPublicCursor:
    """帖子公开信息流游标分页端点测试。"""

    def _create_post(self, client, headers, topic_type="school_major",
                     topic_key="清华大学|计算机", content="测试帖子"):
        resp = client.post(
            "/api/posts",
            headers=headers,
            json={
                "topic_type": topic_type,
                "topic_key": topic_key,
                "content": content,
            },
        )
        assert resp.status_code == 201
        return resp.json()

    def test_first_page_returns_correct_count(self, auth_headers, client):
        """page_size=2 时第一页返回 2 条且 has_more=True。"""
        for i in range(5):
            self._create_post(client, auth_headers, content=f"帖子-{i}")

        resp = client.get("/api/posts/public/cursor?page_size=2")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 2
        assert data["has_more"] is True
        assert data["next_cursor"] is not None

    def test_second_page_uses_next_cursor(self, auth_headers, client):
        """第二页使用 next_cursor 应返回 2 条且 has_more=True。"""
        for i in range(5):
            self._create_post(client, auth_headers, content=f"帖子-{i}")

        page1 = client.get("/api/posts/public/cursor?page_size=2").json()
        page2 = client.get(
            "/api/posts/public/cursor?page_size=2&cursor=" + page1["next_cursor"]
        ).json()

        assert len(page2["items"]) == 2
        assert page2["has_more"] is True
        # 两页 id 不重复
        ids1 = {it["id"] for it in page1["items"]}
        ids2 = {it["id"] for it in page2["items"]}
        assert ids1.isdisjoint(ids2)

    def test_third_page_has_no_more(self, auth_headers, client):
        """5 条记录 page_size=2，第 3 页应为最后一页（has_more=False）。"""
        for i in range(5):
            self._create_post(client, auth_headers, content=f"帖子-{i}")

        page1 = client.get("/api/posts/public/cursor?page_size=2").json()
        page2 = client.get(
            "/api/posts/public/cursor?page_size=2&cursor=" + page1["next_cursor"]
        ).json()
        page3 = client.get(
            "/api/posts/public/cursor?page_size=2&cursor=" + page2["next_cursor"]
        ).json()

        assert len(page3["items"]) == 1
        assert page3["has_more"] is False
        assert page3["next_cursor"] is None

    def test_topic_type_filter(self, auth_headers, client):
        """topic_type=school_major 应只返回 school_major 帖子。"""
        # 5 个 school_major
        for i in range(5):
            self._create_post(client, auth_headers, content=f"校专-{i}")
        # 1 个 company_position
        self._create_post(
            client, auth_headers,
            topic_type="company_position",
            topic_key="腾讯|后端",
            content="公司岗位帖",
        )

        resp = client.get(
            "/api/posts/public/cursor?page_size=20&topic_type=school_major"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 5
        for it in data["items"]:
            assert it["topic_type"] == "school_major"

    def test_empty_result(self, client):
        """无帖子时应返回空 items 且 has_more=False。"""
        resp = client.get("/api/posts/public/cursor?page_size=10")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["has_more"] is False
        assert data["next_cursor"] is None

    def test_invalid_cursor_does_not_crash(self, client):
        """无效 cursor 不应导致 500 错误。"""
        resp = client.get(
            "/api/posts/public/cursor?page_size=10&cursor=not-a-valid-cursor"
        )
        # 实现策略：无效 cursor 被忽略，按第一页返回
        assert resp.status_code == 200

    def test_invalid_topic_type_returns_422(self, client):
        """无效 topic_type 应返回 422。"""
        resp = client.get(
            "/api/posts/public/cursor?page_size=10&topic_type=invalid_type"
        )
        assert resp.status_code == 422

    def test_only_top_level_posts_returned(self, auth_headers, client):
        """parent_id 非空的回复帖不应出现在公开信息流中。"""
        top = self._create_post(client, auth_headers, content="顶层帖")
        # 创建一条回复
        client.post(
            "/api/posts",
            headers=auth_headers,
            json={
                "topic_type": "school_major",
                "topic_key": "清华大学|计算机",
                "content": "这是一条回复",
                "parent_id": top["id"],
            },
        )

        resp = client.get("/api/posts/public/cursor?page_size=10")
        data = resp.json()
        # 只有 1 条顶层帖
        assert len(data["items"]) == 1
        assert data["items"][0]["content"] == "顶层帖"
        assert data["items"][0]["parent_id"] is None


# ======================================================================
# GET /api/mentors/kaoyan-mentors/cursor
# ======================================================================

class TestMentorsCursor:
    """考研导师游标分页端点测试。"""

    def _seed_mentors(self, db_session):
        """创建 3 个导师，不同 university / avg_rating。"""
        m1 = Mentor(
            name="张三", university="清华大学", department="计算机系",
            title="教授", avg_rating=4.5,
        )
        m2 = Mentor(
            name="李四", university="北京大学", department="数学系",
            title="副教授", avg_rating=4.0,
        )
        m3 = Mentor(
            name="王五", university="清华大学", department="物理系",
            title="讲师", avg_rating=3.5,
        )
        db_session.add_all([m1, m2, m3])
        db_session.commit()
        return [m1, m2, m3]

    def test_list_all_mentors(self, client, db_session):
        """无过滤条件应返回全部 3 个导师。"""
        self._seed_mentors(db_session)
        resp = client.get("/api/mentors/kaoyan-mentors/cursor?page_size=10")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 3

    def test_university_filter(self, client, db_session):
        """university=清华 应只返回清华大学的 2 个导师。"""
        self._seed_mentors(db_session)
        resp = client.get(
            "/api/mentors/kaoyan-mentors/cursor?page_size=10&university=清华"
        )
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 2
        for it in items:
            assert "清华" in it["university"]

    def test_min_rating_filter(self, client, db_session):
        """min_rating=4.0 应只返回 avg_rating >= 4.0 的导师。"""
        self._seed_mentors(db_session)
        resp = client.get(
            "/api/mentors/kaoyan-mentors/cursor?page_size=10&min_rating=4.0"
        )
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 2  # 4.5 + 4.0
        for it in items:
            assert it["avg_rating"] >= 4.0

    def test_pagination_has_more(self, client, db_session):
        """page_size=2 + 3 条数据 → 第一页 has_more=True，第二页 has_more=False。"""
        self._seed_mentors(db_session)
        page1 = client.get(
            "/api/mentors/kaoyan-mentors/cursor?page_size=2"
        ).json()
        assert len(page1["items"]) == 2
        assert page1["has_more"] is True
        assert page1["next_cursor"] is not None

        page2 = client.get(
            "/api/mentors/kaoyan-mentors/cursor?page_size=2&cursor="
            + page1["next_cursor"]
        ).json()
        assert len(page2["items"]) == 1
        assert page2["has_more"] is False

    def test_empty_result(self, client):
        """无导师时应返回空列表。"""
        resp = client.get("/api/mentors/kaoyan-mentors/cursor?page_size=10")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["has_more"] is False

    def test_combined_filters(self, client, db_session):
        """university + min_rating 组合过滤。"""
        self._seed_mentors(db_session)
        resp = client.get(
            "/api/mentors/kaoyan-mentors/cursor?page_size=10"
            "&university=清华&min_rating=4.0"
        )
        assert resp.status_code == 200
        items = resp.json()["items"]
        # 只有清华大学的张三（4.5）满足
        assert len(items) == 1
        assert items[0]["name"] == "张三"


# ======================================================================
# GET /api/employment/schools/cursor
# ======================================================================

class TestSchoolsCursor:
    """院校游标分页端点测试 — 仅返回有 published 报告的院校。"""

    def _seed_schools(self, db_session):
        """创建 2 个有 published 报告的院校 + 1 个只有 pending 报告的院校。"""
        s1 = School(name="清华大学", slug="tsinghua", code="10003")
        s2 = School(name="北京大学", slug="pku", code="10001")
        s3 = School(name="复旦大学", slug="fudan", code="10246")
        db_session.add_all([s1, s2, s3])
        db_session.commit()

        # s1, s2 各加 2 份 published 报告
        for s in [s1, s2]:
            for year in [2023, 2024]:
                db_session.add(ReportRecord(
                    school_id=s.id, year=year, source_url=f"url-{s.id}-{year}",
                    parse_status=ParseStatus.published,
                ))
        # s3 只有 pending 报告
        db_session.add(ReportRecord(
            school_id=s3.id, year=2024, source_url="url-pending",
            parse_status=ParseStatus.pending,
        ))
        db_session.commit()
        return s1, s2, s3

    def test_only_published_schools_returned(self, client, db_session):
        """只有 published 报告的院校应返回，pending 的应被排除。"""
        self._seed_schools(db_session)
        resp = client.get("/api/employment/schools/cursor?page_size=10")
        assert resp.status_code == 200
        items = resp.json()["items"]
        names = [it["name"] for it in items]
        assert "清华大学" in names
        assert "北京大学" in names
        assert "复旦大学" not in names  # pending 报告的院校被排除

    def test_pagination(self, client, db_session):
        """2 个有效院校 + page_size=1 → 第一页 has_more=True。"""
        self._seed_schools(db_session)
        page1 = client.get("/api/employment/schools/cursor?page_size=1").json()
        assert len(page1["items"]) == 1
        assert page1["has_more"] is True
        assert page1["next_cursor"] is not None

        page2 = client.get(
            "/api/employment/schools/cursor?page_size=1&cursor="
            + page1["next_cursor"]
        ).json()
        assert len(page2["items"]) == 1
        assert page2["has_more"] is False

    def test_empty_result(self, client):
        """无院校数据时应返回空列表。"""
        resp = client.get("/api/employment/schools/cursor?page_size=10")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["has_more"] is False

    def test_no_duplicate_schools(self, client, db_session):
        """每所学校有多份 published 报告时不应重复返回。"""
        s1 = School(name="清华大学", slug="tsinghua", code="10003")
        db_session.add(s1)
        db_session.commit()
        # 加 3 份 published 报告
        for year in [2022, 2023, 2024]:
            db_session.add(ReportRecord(
                school_id=s1.id, year=year, source_url=f"url-{year}",
                parse_status=ParseStatus.published,
            ))
        db_session.commit()

        resp = client.get("/api/employment/schools/cursor?page_size=10")
        items = resp.json()["items"]
        # 不应因为 3 份报告而返回 3 个清华
        assert len(items) == 1
        assert items[0]["name"] == "清华大学"

    def test_invalid_cursor_does_not_crash(self, client, db_session):
        """无效 cursor 不应导致 500 错误。"""
        self._seed_schools(db_session)
        resp = client.get(
            "/api/employment/schools/cursor?page_size=10&cursor=invalid"
        )
        assert resp.status_code == 200
