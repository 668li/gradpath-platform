# Phase 6 社区讨论功能 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在社区聚合、面试聚合、就业探索三个结果页底部嵌入可复用的讨论区组件，支持发帖、回复、编辑、删除。

**Architecture:** 新增 Post 模型（topic_type + topic_key + content + parent_id 两级嵌套），后端 4 个 REST 端点（GET/POST/PUT/DELETE `/api/posts`），前端 DiscussionSection 可复用组件嵌入 3 个已有结果页。

**Tech Stack:** FastAPI + SQLAlchemy + Pydantic（后端）；Next.js 14 + React + TypeScript + Tailwind（前端）

---

## File Structure

**Backend (新建/修改):**
- Create: `backend/app/models/post.py` — Post 模型 + PostTopicType 枚举
- Modify: `backend/app/models/__init__.py` — 导出 Post、PostTopicType
- Create: `backend/app/schemas/post.py` — Pydantic schemas
- Create: `backend/app/services/post_service.py` — 帖子 CRUD + 级联删除 + 权限校验
- Create: `backend/app/api/posts.py` — 4 个 REST 端点
- Modify: `backend/app/main.py` — 注册 posts router
- Create: `backend/tests/test_api_posts.py` — ~12 个测试用例
- Create: `backend/app/seed/seed_posts.py` — 种子数据（15 条帖子）

**Frontend (新建/修改):**
- Create: `frontend/components/discussion-section.tsx` — 可复用讨论区组件
- Modify: `frontend/types/index.ts` — 新增 Post 相关类型
- Modify: `frontend/lib/api.ts` — 新增 postsApi
- Modify: `frontend/app/(app)/community/result/page.tsx` — 嵌入 DiscussionSection
- Modify: `frontend/app/(app)/interview/result/page.tsx` — 嵌入 DiscussionSection
- Modify: `frontend/app/(app)/explore/result/page.tsx` — 嵌入 DiscussionSection

---

## Task 1: Post 模型与枚举

**Files:**
- Create: `backend/app/models/post.py`
- Modify: `backend/app/models/__init__.py`

- [ ] **Step 1: 创建 Post 模型**

```python
# backend/app/models/post.py
"""讨论帖模型 — 用户围绕"学校专业去向"或"公司岗位面试"主题发帖讨论。"""
import enum
from uuid import UUID

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin


class PostTopicType(str, enum.Enum):
    school_major = "school_major"
    company_position = "company_position"


class Post(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "posts"

    topic_type: Mapped[PostTopicType] = mapped_column(
        Enum(PostTopicType), nullable=False
    )
    topic_key: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    parent_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("posts.id", ondelete="CASCADE"), nullable=True
    )

    # 自引用关系：顶层帖的 replies 列表
    replies: Mapped[list["Post"]] = relationship(
        "Post",
        back_populates="parent",
        cascade="all, delete-orphan",
        foreign_keys=[parent_id],
    )
    parent: Mapped["Post | None"] = relationship(
        "Post",
        back_populates="replies",
        remote_side="Post.id",
        foreign_keys=[parent_id],
    )
```

- [ ] **Step 2: 在 models/__init__.py 中导出**

在 `__init__.py` 中添加导入和导出：

```python
from app.models.post import Post, PostTopicType
```

在 `__all__` 列表中添加 `"Post", "PostTopicType"`。

- [ ] **Step 3: 验证模型加载**

Run: `cd /workspace/backend && python -c "from app.models import Post, PostTopicType; print('OK')"`
Expected: OK

- [ ] **Step 4: Commit**

```bash
git add backend/app/models/post.py backend/app/models/__init__.py
git commit -m "feat: add Post model with PostTopicType enum"
```

---

## Task 2: Post Schemas

**Files:**
- Create: `backend/app/schemas/post.py`

- [ ] **Step 1: 创建 Pydantic schemas**

```python
# backend/app/schemas/post.py
"""讨论帖的 Pydantic Schema 定义。"""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class PostCreate(BaseModel):
    topic_type: str
    topic_key: str = Field(..., max_length=500)
    content: str = Field(..., min_length=1, max_length=2000)
    parent_id: str | None = None


class PostUpdate(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)


class PostResponse(BaseModel):
    id: str
    topic_type: str
    topic_key: str
    content: str
    author_id: str
    author_name: str
    parent_id: str | None = None
    created_at: datetime
    updated_at: datetime
    replies: list["PostResponse"] = []

    model_config = {"from_attributes": True}

    @field_validator("id", "author_id", "parent_id", mode="before")
    @classmethod
    def convert_uuid(cls, v):
        if v is None:
            return v
        return str(v) if hasattr(v, "hex") else v

    @field_validator("topic_type", mode="before")
    @classmethod
    def convert_enum(cls, v):
        if v is None:
            return v
        return v.value if hasattr(v, "value") else str(v)


class PostListResponse(BaseModel):
    items: list[PostResponse]
    total: int
    page: int
    page_size: int
```

- [ ] **Step 2: 验证 schema 加载**

Run: `cd /workspace/backend && python -c "from app.schemas.post import PostCreate, PostResponse; print('OK')"`
Expected: OK

- [ ] **Step 3: Commit**

```bash
git add backend/app/schemas/post.py
git commit -m "feat: add Post schemas"
```

---

## Task 3: Post Service

**Files:**
- Create: `backend/app/services/post_service.py`

- [ ] **Step 1: 创建 post_service.py**

```python
# backend/app/services/post_service.py
"""讨论帖服务层 — 发帖、回复、编辑、删除、列表查询。"""
import uuid
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.post import Post, PostTopicType
from app.models.user import User
from app.schemas.post import PostCreate, PostListResponse, PostResponse, PostUpdate


def _to_response(post: Post, author: User | None = None) -> PostResponse:
    """将 Post ORM 对象转为 PostResponse，附带作者信息。"""
    author_name = author.name if author else "未知用户"
    replies = [
        _to_reply_dict(r) for r in sorted(post.replies, key=lambda x: x.created_at)
    ]
    return PostResponse(
        id=str(post.id),
        topic_type=post.topic_type.value if hasattr(post.topic_type, "value") else post.topic_type,
        topic_key=post.topic_key,
        content=post.content,
        author_id=str(post.user_id),
        author_name=author_name,
        parent_id=str(post.parent_id) if post.parent_id else None,
        created_at=post.created_at,
        updated_at=post.updated_at,
        replies=replies,
    )


def _to_reply_dict(reply: Post) -> dict:
    """将回复帖转为 dict（不含嵌套 replies）。"""
    return {
        "id": str(reply.id),
        "topic_type": reply.topic_type.value if hasattr(reply.topic_type, "value") else reply.topic_type,
        "topic_key": reply.topic_key,
        "content": reply.content,
        "author_id": str(reply.user_id),
        "author_name": "回复者",
        "parent_id": str(reply.parent_id) if reply.parent_id else None,
        "created_at": reply.created_at,
        "updated_at": reply.updated_at,
        "replies": [],
    }


def _resolve_author_name(db: Session, user_id: UUID) -> str:
    """查询用户名。"""
    user = db.query(User).filter(User.id == user_id).first()
    return user.name if user else "未知用户"


def list_posts(
    db: Session,
    topic_type: str,
    topic_key: str,
    page: int = 1,
    page_size: int = 20,
) -> PostListResponse:
    """按主题查询顶层帖列表，每帖附带回复。"""
    try:
        tt = PostTopicType(topic_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"无效的 topic_type: {topic_type}",
        )

    base_q = db.query(Post).filter(
        Post.topic_type == tt,
        Post.topic_key == topic_key,
        Post.parent_id.is_(None),
    )
    total = base_q.count()
    offset = (page - 1) * page_size
    top_posts = (
        base_q.order_by(Post.created_at.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    # 批量查询作者名
    user_ids = {p.user_id for p in top_posts}
    for p in top_posts:
        user_ids.update(r.user_id for r in p.replies)
    users = (
        db.query(User).filter(User.id.in_(list(user_ids))).all()
        if user_ids else []
    )
    user_map = {u.id: u.name for u in users}

    items = []
    for p in top_posts:
        resp = _to_response(p)
        resp.author_name = user_map.get(p.user_id, "未知用户")
        for r in resp.replies:
            r["author_name"] = user_map.get(
                uuid.UUID(r["author_id"]), "未知用户"
            )
        items.append(resp)

    return PostListResponse(
        items=items, total=total, page=page, page_size=page_size
    )


def create_post(db: Session, user: User, data: PostCreate) -> PostResponse:
    """发帖或回复。"""
    try:
        tt = PostTopicType(data.topic_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"无效的 topic_type: {data.topic_type}",
        )

    parent_id: UUID | None = None
    if data.parent_id:
        try:
            parent_id = uuid.UUID(data.parent_id)
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="无效的 parent_id 格式",
            )
        parent = db.query(Post).filter(Post.id == parent_id).first()
        if not parent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="父帖不存在",
            )
        if parent.topic_type != tt or parent.topic_key != data.topic_key:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="回复帖的 topic_type 和 topic_key 必须与父帖一致",
            )
        if parent.parent_id is not None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="不支持多级回复，只能回复顶层帖",
            )

    post = Post(
        topic_type=tt,
        topic_key=data.topic_key,
        content=data.content,
        user_id=user.id,
        parent_id=parent_id,
    )
    db.add(post)
    db.commit()
    db.refresh(post)

    resp = _to_response(post, user)
    return resp


def update_post(
    db: Session, user: User, post_id: str, data: PostUpdate
) -> PostResponse:
    """编辑帖子内容（仅作者）。"""
    try:
        pid = uuid.UUID(post_id)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="帖子不存在"
        )

    post = db.query(Post).filter(Post.id == pid).first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="帖子不存在"
        )
    if post.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只能编辑自己的帖子",
        )

    post.content = data.content
    db.commit()
    db.refresh(post)

    author_name = _resolve_author_name(db, post.user_id)
    resp = _to_response(post)
    resp.author_name = author_name
    return resp


def delete_post(db: Session, user: User, post_id: str) -> None:
    """删除帖子（仅作者）。顶层帖级联删除所有回复。"""
    try:
        pid = uuid.UUID(post_id)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="帖子不存在"
        )

    post = db.query(Post).filter(Post.id == pid).first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="帖子不存在"
        )
    if post.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只能删除自己的帖子",
        )

    db.delete(post)
    db.commit()
```

- [ ] **Step 2: 验证 service 加载**

Run: `cd /workspace/backend && python -c "from app.services.post_service import list_posts, create_post; print('OK')"`
Expected: OK

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/post_service.py
git commit -m "feat: add post_service with CRUD, cascade delete, permission checks"
```

---

## Task 4: Post API 路由

**Files:**
- Create: `backend/app/api/posts.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: 创建 posts API 路由**

```python
# backend/app/api/posts.py
"""讨论帖 API 路由。"""
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.post import (
    PostCreate,
    PostListResponse,
    PostResponse,
    PostUpdate,
)
from app.services.post_service import (
    create_post,
    delete_post,
    list_posts,
    update_post,
)

router = APIRouter(prefix="/api/posts", tags=["讨论帖"])


@router.get("", response_model=PostListResponse)
def list(
    topic_type: str = Query(...),
    topic_key: str = Query(...),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return list_posts(db, topic_type, topic_key, page, page_size)


@router.post("", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
def create(
    body: PostCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return create_post(db, user, body)


@router.put("/{post_id}", response_model=PostResponse)
def update(
    post_id: str,
    body: PostUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return update_post(db, user, post_id, body)


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(
    post_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    delete_post(db, user, post_id)
```

- [ ] **Step 2: 在 main.py 中注册 router**

在 `main.py` 中添加导入和注册：

```python
from app.api.posts import router as posts_router
```

在 `app.include_router(...)` 块中添加：

```python
app.include_router(posts_router)
```

- [ ] **Step 3: 验证路由注册**

Run: `cd /workspace/backend && python -c "from app.main import app; routes = [r.path for r in app.routes]; assert '/api/posts' in routes; print('OK')"`
Expected: OK

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/posts.py backend/app/main.py
git commit -m "feat: add posts API routes (GET/POST/PUT/DELETE)"
```

---

## Task 5: 后端测试

**Files:**
- Create: `backend/tests/test_api_posts.py`

- [ ] **Step 1: 编写测试文件**

```python
# backend/tests/test_api_posts.py
"""讨论帖 API 测试。"""
import pytest

TOPIC_SCHOOL = "清华大学|计算机科学与技术"
TOPIC_COMPANY = "腾讯|后端开发"


def _create_post(client, headers, topic_type="school_major",
                 topic_key=TOPIC_SCHOOL, content="测试帖子内容",
                 parent_id=None):
    """通过 API 发帖，返回响应。"""
    payload = {
        "topic_type": topic_type,
        "topic_key": topic_key,
        "content": content,
        "parent_id": parent_id,
    }
    return client.post("/api/posts", headers=headers, json=payload)


# ======================================================================
# 发帖
# ======================================================================

class TestCreatePost:
    def test_create_top_level_post(self, auth_headers, client):
        """创建顶层帖成功。"""
        resp = _create_post(client, auth_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["topic_type"] == "school_major"
        assert data["topic_key"] == TOPIC_SCHOOL
        assert data["content"] == "测试帖子内容"
        assert data["author_name"] == "测试用户"
        assert data["parent_id"] is None
        assert data["replies"] == []
        assert "id" in data
        assert "created_at" in data

    def test_create_reply(self, auth_headers, client):
        """回复顶层帖成功。"""
        top = _create_post(client, auth_headers)
        top_id = top.json()["id"]

        resp = _create_post(client, auth_headers, content="这是一条回复",
                            parent_id=top_id)
        assert resp.status_code == 201
        data = resp.json()
        assert data["parent_id"] == top_id
        assert data["content"] == "这是一条回复"

    def test_create_post_empty_content(self, auth_headers, client):
        """空内容发帖返回 422。"""
        resp = _create_post(client, auth_headers, content="")
        assert resp.status_code == 422

    def test_create_post_too_long(self, auth_headers, client):
        """超过 2000 字返回 422。"""
        resp = _create_post(client, auth_headers, content="x" * 2001)
        assert resp.status_code == 422

    def test_reply_nonexistent_parent(self, auth_headers, client):
        """回复不存在的父帖返回 404。"""
        fake_id = "00000000-0000-0000-0000-000000000000"
        resp = _create_post(client, auth_headers, parent_id=fake_id)
        assert resp.status_code == 404

    def test_reply_topic_mismatch(self, auth_headers, client):
        """回复帖 topic 与父帖不一致返回 422。"""
        top = _create_post(client, auth_headers)
        top_id = top.json()["id"]

        resp = _create_post(client, auth_headers,
                            topic_key="其他学校|其他专业",
                            parent_id=top_id)
        assert resp.status_code == 422

    def test_reply_to_reply_rejected(self, auth_headers, client):
        """回复回复帖（多级嵌套）返回 422。"""
        top = _create_post(client, auth_headers)
        top_id = top.json()["id"]
        reply = _create_post(client, auth_headers, parent_id=top_id,
                             content="第一条回复")
        reply_id = reply.json()["id"]

        resp = _create_post(client, auth_headers, parent_id=reply_id,
                            content="回复回复")
        assert resp.status_code == 422

    def test_anonymous_create_fails(self, client):
        """未登录不能发帖。"""
        resp = _create_post(client, {}, )
        assert resp.status_code == 401


# ======================================================================
# 列表查询
# ======================================================================

class TestListPosts:
    def test_list_posts_with_replies(self, auth_headers, client):
        """列表返回顶层帖及其回复。"""
        top1 = _create_post(client, auth_headers, content="第一个帖子")
        top2 = _create_post(client, auth_headers, content="第二个帖子")
        reply = _create_post(client, auth_headers, content="回复第一个",
                             parent_id=top1.json()["id"])

        resp = client.get(
            "/api/posts",
            params={"topic_type": "school_major", "topic_key": TOPIC_SCHOOL},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

        # 按创建时间降序，top2 在前
        first = data["items"][0]
        assert first["content"] == "第二个帖子"
        assert first["replies"] == []

        second = data["items"][1]
        assert second["content"] == "第一个帖子"
        assert len(second["replies"]) == 1
        assert second["replies"][0]["content"] == "回复第一个"

    def test_list_posts_empty(self, client):
        """无帖时返回空列表。"""
        resp = client.get(
            "/api/posts",
            params={"topic_type": "company_position",
                    "topic_key": "字节跳动|算法工程师"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["items"] == []

    def test_list_posts_pagination(self, auth_headers, client):
        """分页：page_size=1 时每页 1 条。"""
        for i in range(3):
            _create_post(client, auth_headers, content=f"帖子{i}")

        resp = client.get(
            "/api/posts",
            params={"topic_type": "school_major", "topic_key": TOPIC_SCHOOL,
                    "page": 1, "page_size": 1},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 3
        assert len(data["items"]) == 1
        assert data["page"] == 1
        assert data["page_size"] == 1

    def test_list_no_auth_required(self, client):
        """列表查询不需要登录。"""
        resp = client.get(
            "/api/posts",
            params={"topic_type": "school_major", "topic_key": TOPIC_SCHOOL},
        )
        assert resp.status_code == 200


# ======================================================================
# 编辑
# ======================================================================

class TestUpdatePost:
    def test_update_own_post(self, auth_headers, client):
        """编辑自己的帖子。"""
        post = _create_post(client, auth_headers)
        post_id = post.json()["id"]

        resp = client.put(
            f"/api/posts/{post_id}",
            headers=auth_headers,
            json={"content": "修改后的内容"},
        )
        assert resp.status_code == 200
        assert resp.json()["content"] == "修改后的内容"

    def test_update_others_post(self, auth_headers, client):
        """不能编辑他人帖子（403）。"""
        # 用第一个账号发帖
        post = _create_post(client, auth_headers)
        post_id = post.json()["id"]

        # 注册第二个账号
        client.post(
            "/api/auth/register",
            json={"email": "other@example.com", "password": "Test1234!",
                  "name": "其他用户"},
        )
        resp_login = client.post(
            "/api/auth/login",
            json={"email": "other@example.com", "password": "Test1234!"},
        )
        other_headers = {"Authorization": f"Bearer {resp_login.json()['access_token']}"}

        resp = client.put(
            f"/api/posts/{post_id}",
            headers=other_headers,
            json={"content": "恶意修改"},
        )
        assert resp.status_code == 403

    def test_update_nonexistent(self, auth_headers, client):
        """编辑不存在的帖子返回 404。"""
        fake_id = "00000000-0000-0000-0000-000000000000"
        resp = client.put(
            f"/api/posts/{fake_id}",
            headers=auth_headers,
            json={"content": "内容"},
        )
        assert resp.status_code == 404


# ======================================================================
# 删除
# ======================================================================

class TestDeletePost:
    def test_delete_own_post(self, auth_headers, client):
        """删除自己的帖子。"""
        post = _create_post(client, auth_headers)
        post_id = post.json()["id"]

        resp = client.delete(f"/api/posts/{post_id}", headers=auth_headers)
        assert resp.status_code == 204

        # 确认已删除
        resp_list = client.get(
            "/api/posts",
            params={"topic_type": "school_major", "topic_key": TOPIC_SCHOOL},
        )
        assert resp_list.json()["total"] == 0

    def test_cascade_delete(self, auth_headers, client):
        """删除顶层帖级联删除所有回复。"""
        top = _create_post(client, auth_headers)
        top_id = top.json()["id"]
        _create_post(client, auth_headers, parent_id=top_id, content="回复1")
        _create_post(client, auth_headers, parent_id=top_id, content="回复2")

        # 删除顶层帖
        resp = client.delete(f"/api/posts/{top_id}", headers=auth_headers)
        assert resp.status_code == 204

        # 确认帖子和回复都被删除
        resp_list = client.get(
            "/api/posts",
            params={"topic_type": "school_major", "topic_key": TOPIC_SCHOOL},
        )
        assert resp_list.json()["total"] == 0

    def test_delete_others_post(self, auth_headers, client):
        """不能删除他人帖子（403）。"""
        post = _create_post(client, auth_headers)
        post_id = post.json()["id"]

        # 注册第二个账号
        client.post(
            "/api/auth/register",
            json={"email": "other2@example.com", "password": "Test1234!",
                  "name": "其他用户2"},
        )
        resp_login = client.post(
            "/api/auth/login",
            json={"email": "other2@example.com", "password": "Test1234!"},
        )
        other_headers = {"Authorization": f"Bearer {resp_login.json()['access_token']}"}

        resp = client.delete(f"/api/posts/{post_id}", headers=other_headers)
        assert resp.status_code == 403
```

- [ ] **Step 2: 运行测试**

Run: `cd /workspace/backend && python -m pytest tests/test_api_posts.py -v --tb=short`
Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_api_posts.py
git commit -m "test: add 16 post API tests (CRUD, permissions, cascade, pagination)"
```

---

## Task 6: 种子数据

**Files:**
- Create: `backend/app/seed/__init__.py`
- Create: `backend/app/seed/seed_posts.py`

- [ ] **Step 1: 创建 seed 包**

创建空文件 `backend/app/seed/__init__.py`。

- [ ] **Step 2: 创建 seed_posts.py**

```python
# backend/app/seed/seed_posts.py
"""讨论帖种子数据。"""
import uuid

from sqlalchemy.orm import Session

from app.models.post import Post, PostTopicType
from app.models.user import User


SEED_TOPICS = [
    ("清华大学|计算机科学与技术", "school_major", 5, 5),
    ("腾讯|后端开发", "company_position", 3, 2),
    ("字节跳动|算法工程师", "company_position", 0, 0),
]

SEED_CONTENTS = {
    "清华大学|计算机科学与技术": {
        "posts": [
            "请问这个专业去字节的多吗？",
            "今年秋招感觉怎么样，大家拿到的 offer 都是什么方向？",
            "想了解一下保研和就业的比例，有学长学姐分享一下吗？",
            "听说今年互联网寒冬，计算机专业还值得读吗？",
            "有没有去国企的同学，待遇和发展怎么样？",
        ],
        "replies": [
            "挺多的，今年去了好几个",
            "今年确实比往年难一些，但头部公司还是有机会的",
            "保研率大概 30% 左右，每年有波动",
            "寒冬是暂时的，长期来看还是不错的",
            "国企待遇一般但稳定，看个人选择",
        ],
    },
    "腾讯|后端开发": {
        "posts": [
            "腾讯后端面试主要考什么？算法多还是系统设计多？",
            "PCG 和 CSIG 的后端开发哪个更好？",
            "面试后多久能收到结果通知？",
        ],
        "replies": [
            "算法和系统设计都有，看部门",
            "各有优劣，看个人发展偏好",
        ],
    },
}


def seed_posts(db: Session) -> None:
    """插入讨论帖种子数据。"""
    # 获取或创建一个种子用户
    seed_user = db.query(User).filter(User.email == "demo@gradpath.com").first()
    if not seed_user:
        seed_user = User(
            email="demo@gradpath.com",
            password_hash="$2b$12$dummyhashforseeduseronly",
            name="社区达人",
        )
        db.add(seed_user)
        db.flush()

    second_user = db.query(User).filter(User.email == "demo2@gradpath.com").first()
    if not second_user:
        second_user = User(
            email="demo2@gradpath.com",
            password_hash="$2b$12$dummyhashforseeduseronly2",
            name="热心校友",
        )
        db.add(second_user)
        db.flush()

    for topic_key, topic_type_str, post_count, reply_count in SEED_TOPICS:
        if post_count == 0:
            continue
        topic_type = PostTopicType(topic_type_str)
        contents = SEED_CONTENTS[topic_key]
        users = [seed_user, second_user]

        for i in range(post_count):
            post = Post(
                topic_type=topic_type,
                topic_key=topic_key,
                content=contents["posts"][i],
                user_id=users[i % 2].id,
                parent_id=None,
            )
            db.add(post)
            db.flush()

            if i < reply_count:
                reply = Post(
                    topic_type=topic_type,
                    topic_key=topic_key,
                    content=contents["replies"][i],
                    user_id=users[(i + 1) % 2].id,
                    parent_id=post.id,
                )
                db.add(reply)

    db.commit()
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/seed/__init__.py backend/app/seed/seed_posts.py
git commit -m "feat: add seed_posts with 15 posts across 3 topics"
```

---

## Task 7: 前端类型定义

**Files:**
- Modify: `frontend/types/index.ts`

- [ ] **Step 1: 在 types/index.ts 末尾追加 Post 类型**

在文件末尾添加：

```typescript
// ===== 讨论帖 =====
export type PostTopicType = "school_major" | "company_position";

export interface PostItem {
  id: string;
  topic_type: string;
  topic_key: string;
  content: string;
  author_id: string;
  author_name: string;
  parent_id: string | null;
  created_at: string;
  updated_at: string;
  replies: PostItem[];
}

export interface PostListResponse {
  items: PostItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface PostCreate {
  topic_type: string;
  topic_key: string;
  content: string;
  parent_id?: string | null;
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/types/index.ts
git commit -m "feat: add Post types to frontend type definitions"
```

---

## Task 8: 前端 API 客户端

**Files:**
- Modify: `frontend/lib/api.ts`

- [ ] **Step 1: 在 api.ts 中添加 postsApi**

在 `api.ts` 的 import 块中添加 `PostCreate`, `PostListResponse` 到类型导入。

在文件末尾（pipelineApi 之后）添加：

```typescript
// ===== 讨论帖 =====
export const postsApi = {
  list: (params: { topic_type: string; topic_key: string; page?: number; page_size?: number }) =>
    request<PostListResponse>(`/api/posts${buildQuery(params as Record<string, string | undefined | null>)}`),

  create: (body: PostCreate) =>
    request<PostItem>("/api/posts", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  update: (id: string, content: string) =>
    request<PostItem>(`/api/posts/${id}`, {
      method: "PUT",
      body: JSON.stringify({ content }),
    }),

  remove: (id: string) =>
    request<void>(`/api/posts/${id}`, { method: "DELETE" }),
};
```

在 import 中添加 `PostItem` 类型。

- [ ] **Step 2: Commit**

```bash
git add frontend/lib/api.ts
git commit -m "feat: add postsApi to frontend API client"
```

---

## Task 9: DiscussionSection 组件

**Files:**
- Create: `frontend/components/discussion-section.tsx`

- [ ] **Step 1: 创建 DiscussionSection 组件**

```tsx
"use client";

import { useState, useCallback } from "react";
import { MessageSquare, Send, Trash2, Edit2, X, CornerDownRight } from "lucide-react";
import { postsApi } from "@/lib/api";
import { useToast } from "@/components/ui/toast";
import { Button } from "@/components/ui/form-controls";
import { useAuthStore } from "@/stores/auth";
import type { PostItem, PostTopicType } from "@/types";

interface DiscussionSectionProps {
  topicType: PostTopicType;
  topicKey: string;
  title?: string;
}

const MAX_CONTENT = 2000;

/** 相对时间格式化 */
function relativeTime(iso: string): string {
  const now = Date.now();
  const then = new Date(iso).getTime();
  const diff = now - then;
  const min = Math.floor(diff / 60000);
  if (min < 1) return "刚刚";
  if (min < 60) return `${min} 分钟前`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr} 小时前`;
  const day = Math.floor(hr / 24);
  if (day < 30) return `${day} 天前`;
  return new Date(iso).toLocaleDateString("zh-CN");
}

/** 作者头像首字 */
function Avatar({ name }: { name: string }) {
  const initial = name.charAt(0).toUpperCase();
  return (
    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-brand-500 text-sm font-medium text-white">
      {initial}
    </div>
  );
}

/** 帖子内容渲染（URL 转链接，换行保留） */
function renderContent(content: string) {
  const urlRegex = /(https?:\/\/[^\s]+)/g;
  const parts = content.split(urlRegex);
  return parts.map((part, i) => {
    if (urlRegex.test(part)) {
      return (
        <a
          key={i}
          href={part}
          target="_blank"
          rel="noopener noreferrer"
          className="text-brand-600 hover:underline"
        >
          {part}
        </a>
      );
    }
    // 保留换行
    return part.split("\n").map((line, j) => (
      <span key={`${i}-${j}`}>
        {line}
        {j < part.split("\n").length - 1 && <br />}
      </span>
    ));
  });
}

/** 单条帖子卡片 */
function PostCard({
  post,
  currentUserId,
  onReply,
  onEdit,
  onDelete,
}: {
  post: PostItem;
  currentUserId: string | null;
  onReply: (postId: string, content: string) => void;
  onEdit: (postId: string, content: string) => void;
  onDelete: (postId: string) => void;
}) {
  const [showReplyBox, setShowReplyBox] = useState(false);
  const [replyContent, setReplyContent] = useState("");
  const [editing, setEditing] = useState(false);
  const [editContent, setEditContent] = useState(post.content);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const isAuthor = currentUserId === post.author_id;

  const handleReply = () => {
    if (!replyContent.trim()) return;
    onReply(post.id, replyContent);
    setReplyContent("");
    setShowReplyBox(false);
  };

  const handleEdit = () => {
    if (!editContent.trim()) return;
    onEdit(post.id, editContent);
    setEditing(false);
  };

  return (
    <div className="rounded-lg border border-slate-200 p-4">
      <div className="flex items-start gap-3">
        <Avatar name={post.author_name} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-medium text-sm text-slate-800">{post.author_name}</span>
            <span className="text-xs text-slate-400">{relativeTime(post.created_at)}</span>
          </div>

          {editing ? (
            <div className="mt-2 space-y-2">
              <textarea
                value={editContent}
                onChange={(e) => setEditContent(e.target.value)}
                maxLength={MAX_CONTENT}
                rows={3}
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none"
              />
              <div className="flex gap-2">
                <Button size="sm" onClick={handleEdit}>保存</Button>
                <Button size="sm" variant="secondary" onClick={() => { setEditing(false); setEditContent(post.content); }}>
                  取消
                </Button>
              </div>
            </div>
          ) : (
            <p className="mt-1 text-sm text-slate-600 whitespace-pre-wrap break-words">
              {renderContent(post.content)}
            </p>
          )}

          <div className="mt-2 flex items-center gap-3">
            {isAuthor && !editing && (
              <>
                <button
                  onClick={() => setEditing(true)}
                  className="inline-flex items-center gap-1 text-xs text-slate-400 hover:text-brand-600"
                >
                  <Edit2 className="h-3 w-3" /> 编辑
                </button>
                {confirmDelete ? (
                  <span className="inline-flex items-center gap-1">
                    <button
                      onClick={() => onDelete(post.id)}
                      className="text-xs text-red-500 hover:underline"
                    >
                      确认删除
                    </button>
                    <button
                      onClick={() => setConfirmDelete(false)}
                      className="text-xs text-slate-400 hover:underline"
                    >
                      取消
                    </button>
                  </span>
                ) : (
                  <button
                    onClick={() => setConfirmDelete(true)}
                    className="inline-flex items-center gap-1 text-xs text-slate-400 hover:text-red-500"
                  >
                    <Trash2 className="h-3 w-3" /> 删除
                  </button>
                )}
              </>
            )}
          </div>
        </div>
      </div>

      {/* 回复列表 */}
      {post.replies && post.replies.length > 0 && (
        <div className="mt-3 ml-11 space-y-3">
          {post.replies.map((reply) => (
            <div key={reply.id} className="flex items-start gap-2">
              <CornerDownRight className="h-4 w-4 shrink-0 text-slate-300 mt-1" />
              <Avatar name={reply.author_name} />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-xs text-slate-700">{reply.author_name}</span>
                  <span className="text-xs text-slate-400">{relativeTime(reply.created_at)}</span>
                </div>
                <p className="mt-0.5 text-sm text-slate-600 whitespace-pre-wrap break-words">
                  {renderContent(reply.content)}
                </p>
                {currentUserId === reply.author_id && (
                  <ReplyActions
                    reply={reply}
                    currentUserId={currentUserId}
                    onEdit={onEdit}
                    onDelete={onDelete}
                  />
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* 回复输入框 */}
      {showReplyBox && (
        <div className="mt-3 ml-11 space-y-2">
          <textarea
            value={replyContent}
            onChange={(e) => setReplyContent(e.target.value)}
            maxLength={MAX_CONTENT}
            rows={2}
            placeholder="写下你的回复…"
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none"
          />
          <div className="flex gap-2">
            <Button size="sm" onClick={handleReply}>
              <Send className="h-3 w-3" /> 发送回复
            </Button>
            <Button size="sm" variant="secondary" onClick={() => setShowReplyBox(false)}>
              取消
            </Button>
          </div>
        </div>
      )}

      {/* 回复按钮 */}
      {!showReplyBox && (
        <button
          onClick={() => setShowReplyBox(true)}
          className="mt-2 ml-11 inline-flex items-center gap-1 text-xs text-slate-400 hover:text-brand-600"
        >
          <MessageSquare className="h-3 w-3" /> 回复
        </button>
      )}
    </div>
  );
}

/** 回复的操作按钮（编辑/删除） */
function ReplyActions({
  reply,
  currentUserId,
  onEdit,
  onDelete,
}: {
  reply: PostItem;
  currentUserId: string | null;
  onEdit: (postId: string, content: string) => void;
  onDelete: (postId: string) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [editContent, setEditContent] = useState(reply.content);
  const [confirmDelete, setConfirmDelete] = useState(false);

  if (currentUserId !== reply.author_id) return null;

  if (editing) {
    return (
      <div className="mt-1 space-y-1">
        <textarea
          value={editContent}
          onChange={(e) => setEditContent(e.target.value)}
          maxLength={MAX_CONTENT}
          rows={2}
          className="w-full rounded-md border border-slate-300 px-2 py-1 text-sm focus:border-brand-500 focus:outline-none"
        />
        <div className="flex gap-2">
          <button
            onClick={() => {
              if (editContent.trim()) {
                onEdit(reply.id, editContent);
                setEditing(false);
              }
            }}
            className="text-xs text-brand-600 hover:underline"
          >
            保存
          </button>
          <button
            onClick={() => { setEditing(false); setEditContent(reply.content); }}
            className="text-xs text-slate-400 hover:underline"
          >
            取消
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="mt-1 flex items-center gap-2">
      <button
        onClick={() => setEditing(true)}
        className="inline-flex items-center gap-1 text-xs text-slate-400 hover:text-brand-600"
      >
        <Edit2 className="h-3 w-3" /> 编辑
      </button>
      {confirmDelete ? (
        <span className="inline-flex items-center gap-1">
          <button
            onClick={() => onDelete(reply.id)}
            className="text-xs text-red-500 hover:underline"
          >
            确认删除
          </button>
          <button
            onClick={() => setConfirmDelete(false)}
            className="text-xs text-slate-400 hover:underline"
          >
            取消
          </button>
        </span>
      ) : (
        <button
          onClick={() => setConfirmDelete(true)}
          className="inline-flex items-center gap-1 text-xs text-slate-400 hover:text-red-500"
        >
          <Trash2 className="h-3 w-3" /> 删除
        </button>
      )}
    </div>
  );
}

export function DiscussionSection({ topicType, topicKey, title }: DiscussionSectionProps) {
  const [posts, setPosts] = useState<PostItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [newContent, setNewContent] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const toast = useToast();
  const { user } = useAuthStore();

  const loadPosts = useCallback(async (pageNum: number, append: boolean) => {
    try {
      const resp = await postsApi.list({
        topic_type: topicType,
        topic_key: topicKey,
        page: pageNum,
        page_size: 20,
      });
      if (append) {
        setPosts((prev) => [...prev, ...resp.items]);
      } else {
        setPosts(resp.items);
      }
      setTotal(resp.total);
      setPage(resp.page);
    } catch (err) {
      toast.push(err instanceof Error ? err.message : "加载讨论失败", "error");
    } finally {
      setLoading(false);
    }
  }, [topicType, topicKey, toast]);

  // 初始加载
  useState(() => {
    loadPosts(1, false);
  });

  const handleCreate = async () => {
    if (!newContent.trim()) return;
    setSubmitting(true);
    try {
      const created = await postsApi.create({
        topic_type: topicType,
        topic_key: topicKey,
        content: newContent,
      });
      setPosts((prev) => [created, ...prev]);
      setTotal((prev) => prev + 1);
      setNewContent("");
      toast.push("发布成功", "success");
    } catch (err) {
      toast.push(err instanceof Error ? err.message : "发布失败", "error");
    } finally {
      setSubmitting(false);
    }
  };

  const handleReply = async (parentId: string, content: string) => {
    try {
      const reply = await postsApi.create({
        topic_type: topicType,
        topic_key: topicKey,
        content,
        parent_id: parentId,
      });
      setPosts((prev) =>
        prev.map((p) =>
          p.id === parentId
            ? { ...p, replies: [...p.replies, reply] }
            : p
        )
      );
      toast.push("回复成功", "success");
    } catch (err) {
      toast.push(err instanceof Error ? err.message : "回复失败", "error");
    }
  };

  const handleEdit = async (postId: string, content: string) => {
    try {
      const updated = await postsApi.update(postId, content);
      // 更新顶层帖或回复
      setPosts((prev) =>
        prev.map((p) => {
          if (p.id === postId) return updated;
          return {
            ...p,
            replies: p.replies.map((r) =>
              r.id === postId ? { ...r, content: updated.content } : r
            ),
          };
        })
      );
      toast.push("修改成功", "success");
    } catch (err) {
      toast.push(err instanceof Error ? err.message : "修改失败", "error");
    }
  };

  const handleDelete = async (postId: string) => {
    try {
      await postsApi.remove(postId);
      setPosts((prev) =>
        prev
          .filter((p) => p.id !== postId)
          .map((p) => ({
            ...p,
            replies: p.replies.filter((r) => r.id !== postId),
          }))
      );
      setTotal((prev) => Math.max(0, prev - 1));
      toast.push("删除成功", "success");
    } catch (err) {
      toast.push(err instanceof Error ? err.message : "删除失败", "error");
    }
  };

  const loadMore = () => {
    loadPosts(page + 1, true);
  };

  return (
    <div className="card">
      <h2 className="font-semibold text-slate-800 mb-4 flex items-center gap-2">
        <MessageSquare className="h-5 w-5 text-brand-500" />
        {title ?? "讨论区"}
        {total > 0 && (
          <span className="text-sm font-normal text-slate-400">（{total}）</span>
        )}
      </h2>

      {/* 发帖框 */}
      {user ? (
        <div className="mb-4 space-y-2">
          <textarea
            value={newContent}
            onChange={(e) => setNewContent(e.target.value)}
            maxLength={MAX_CONTENT}
            rows={3}
            placeholder="分享你的经验或提出问题…"
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none"
          />
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-400">
              {newContent.length} / {MAX_CONTENT}
            </span>
            <Button
              size="sm"
              onClick={handleCreate}
              disabled={!newContent.trim() || submitting}
            >
              <Send className="h-3 w-3" /> 发布
            </Button>
          </div>
        </div>
      ) : (
        <div className="mb-4 rounded-lg bg-slate-50 px-4 py-3 text-center text-sm text-slate-400">
          <a href="/login" className="text-brand-600 hover:underline">登录</a>
          后参与讨论
        </div>
      )}

      {/* 帖子列表 */}
      {loading ? (
        <p className="text-sm text-slate-400">加载讨论中…</p>
      ) : posts.length === 0 ? (
        <div className="py-8 text-center">
          <MessageSquare className="h-10 w-10 mx-auto text-slate-300" />
          <p className="mt-2 text-sm text-slate-400">还没有人讨论，来说点什么吧</p>
        </div>
      ) : (
        <div className="space-y-3">
          {posts.map((post) => (
            <PostCard
              key={post.id}
              post={post}
              currentUserId={user?.id ?? null}
              onReply={handleReply}
              onEdit={handleEdit}
              onDelete={handleDelete}
            />
          ))}
          {/* 加载更多 */}
          {posts.length < total && (
            <div className="text-center">
              <Button variant="secondary" size="sm" onClick={loadMore}>
                加载更多
              </Button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: 验证组件编译**

Run: `cd /workspace/frontend && npx tsc --noEmit --pretty 2>&1 | head -30`
Expected: No errors related to discussion-section.tsx

- [ ] **Step 3: Commit**

```bash
git add frontend/components/discussion-section.tsx
git commit -m "feat: add DiscussionSection reusable component"
```

---

## Task 10: 嵌入 DiscussionSection 到 3 个结果页

**Files:**
- Modify: `frontend/app/(app)/community/result/page.tsx`
- Modify: `frontend/app/(app)/interview/result/page.tsx`
- Modify: `frontend/app/(app)/explore/result/page.tsx`

- [ ] **Step 1: community/result/page.tsx**

在文件顶部添加 import：
```typescript
import { DiscussionSection } from "@/components/discussion-section";
```

在 `CommunityResultContent` 函数的 return JSX 中，在最后的 CTA `<div className="card bg-brand-50 border-brand-100">` 块之前添加：

```tsx
{/* 讨论区 */}
<DiscussionSection
  topicType="school_major"
  topicKey={`${school}|${major}`}
  title={`${school} · ${major} 讨论`}
/>
```

- [ ] **Step 2: interview/result/page.tsx**

在文件顶部添加 import：
```typescript
import { DiscussionSection } from "@/components/discussion-section";
```

注意：interview/result 页面只有 `company` 参数，没有 `position`。聚合查询时 position 是可选的。讨论区用 `company|` 作为 topic_key（position 为空时）。

在 `InterviewResultContent` 函数的 return JSX 中，在最后的 CTA 块之前添加：

```tsx
{/* 讨论区 */}
<DiscussionSection
  topicType="company_position"
  topicKey={`${company}|`}
  title={`${company} 面试讨论`}
/>
```

- [ ] **Step 3: explore/result/page.tsx**

在文件顶部添加 import：
```typescript
import { DiscussionSection } from "@/components/discussion-section";
```

在 `ExploreResultContent` 函数的 return JSX 中，在最后的 CTA 块之前添加：

```tsx
{/* 讨论区 */}
<DiscussionSection
  topicType="school_major"
  topicKey={`${school}|${major}`}
  title={`${school} · ${major} 讨论`}
/>
```

- [ ] **Step 4: 构建验证**

Run: `cd /workspace/frontend && npm run build 2>&1 | tail -20`
Expected: Build success

- [ ] **Step 5: Commit**

```bash
git add frontend/app/(app)/community/result/page.tsx frontend/app/(app)/interview/result/page.tsx frontend/app/(app)/explore/result/page.tsx
git commit -m "feat: embed DiscussionSection in 3 result pages"
```

---

## Task 11: 全量测试与构建验证

- [ ] **Step 1: 运行全量后端测试**

Run: `cd /workspace/backend && python -m pytest --tb=short -q`
Expected: All tests PASS (162 + 16 = 178)

- [ ] **Step 2: 运行前端构建**

Run: `cd /workspace/frontend && npm run build`
Expected: Build success, 23 routes (20 + 3 pages updated)

- [ ] **Step 3: 种子数据加载测试**

Run: `cd /workspace/backend && python -c "
from app.database import engine, SessionLocal
from app.models.base import Base
from app.seed.seed_posts import seed_posts
Base.metadata.create_all(engine)
db = SessionLocal()
seed_posts(db)
from app.models.post import Post
print(f'Total posts: {db.query(Post).count()}')
db.close()
"`
Expected: Total posts: 15

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "chore: Phase 6 complete - community discussion feature"
```
