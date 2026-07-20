# tests/test_bookmarks.py
"""收藏功能单元测试。"""
from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))


def test_bookmark_model_import():
    from app.models.bookmark import Bookmark, BookmarkTargetType

    assert Bookmark.__tablename__ == "bookmarks"
    assert BookmarkTargetType.school.value == "school"
    assert BookmarkTargetType.mentor.value == "mentor"
    assert BookmarkTargetType.post.value == "post"


def test_bookmark_schema():
    from app.schemas.bookmark import BookmarkCreate, BookmarkResponse, BookmarkListResponse

    create = BookmarkCreate(target_type="school", target_id="123")
    assert create.target_type == "school"
    assert create.target_id == "123"


def test_bookmark_api_exists():
    from app.api.bookmarks import router

    routes = {r.path for r in router.routes}
    assert "" in routes or "/" in routes or any("bookmarks" in r.path for r in router.routes)
