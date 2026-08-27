"""质量分反馈闭环 API 测试（Phase I）。

覆盖：401 未登录 / 404 目标不存在 / upsert 替换（同用户同条目只留最新）/
429 限流 / 经验贴与资讯双目标类型 / 非法 target_id。
"""

import uuid

from app.models.experience_post import ExperiencePost
from app.models.kaoyan_news import KaoyanNews
from app.models.quality_feedback import QualityFeedback
from app.models.user import User

POST_URL = "/api/kaoyan/quality-feedback"


def _ensure_user(db_session) -> User:
    user = db_session.query(User).first()
    if user is None:
        user = User(email="owner@example.com", name="作者", password_hash="x")
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
    return user


def _make_experience_post(db_session) -> ExperiencePost:
    post = ExperiencePost(
        title="测试经验贴",
        content="正文内容" * 50,
        summary="摘要",
        user_id=_ensure_user(db_session).id,
        source_platform="bilibili",
        source_url="https://bilibili.com/video/1",
        status="approved",
        quality_score=80,
        quality_grade="A",
    )
    db_session.add(post)
    db_session.commit()
    db_session.refresh(post)
    return post


def _make_kaoyan_news(db_session) -> KaoyanNews:
    news = KaoyanNews(
        title="测试资讯",
        summary="摘要",
        source_platform="eol_kaoyan",
        source_url="https://eol.cn/news/1",
        status="approved",
        quality_score=80,
        quality_grade="A",
    )
    db_session.add(news)
    db_session.commit()
    db_session.refresh(news)
    return news


def test_feedback_requires_auth(client):
    resp = client.post(
        POST_URL,
        json={
            "target_type": "experience_post",
            "target_id": "a" * 32,
            "feedback_type": "helpful",
        },
    )
    assert resp.status_code == 401


def test_feedback_target_not_found(client, auth_headers):
    resp = client.post(
        POST_URL,
        headers=auth_headers,
        json={
            "target_type": "experience_post",
            "target_id": "a" * 32,
            "feedback_type": "helpful",
        },
    )
    assert resp.status_code == 404


def test_feedback_rejects_malformed_target_id(client, auth_headers):
    # 长度达标（32）但非合法 UUID 格式 → 视为目标不存在（404）
    resp = client.post(
        POST_URL,
        headers=auth_headers,
        json={
            "target_type": "experience_post",
            "target_id": "z" * 32,
            "feedback_type": "helpful",
        },
    )
    assert resp.status_code == 404

    # 长度不达标（过短）→ schema 校验拒绝（422）
    resp = client.post(
        POST_URL,
        headers=auth_headers,
        json={
            "target_type": "experience_post",
            "target_id": "not-a-uuid!",
            "feedback_type": "helpful",
        },
    )
    assert resp.status_code == 422


def test_feedback_create_and_upsert_switch(client, auth_headers, db_session):
    post = _make_experience_post(db_session)
    target_id = str(post.id)  # 前端回传的是 API 序列化的带连字符 UUID

    # 首次：👍 helpful + 选填原因
    resp = client.post(
        POST_URL,
        headers=auth_headers,
        json={
            "target_type": "experience_post",
            "target_id": target_id,
            "feedback_type": "helpful",
            "reason": "证据链很清楚",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["feedback_type"] == "helpful"
    assert body["reason"] == "证据链很清楚"
    assert body["target_id"] == uuid.UUID(target_id).hex

    # 切换：👎 unhelpful（upsert 替换，不新增行）
    resp = client.post(
        POST_URL,
        headers=auth_headers,
        json={
            "target_type": "experience_post",
            "target_id": target_id,
            "feedback_type": "unhelpful",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["feedback_type"] == "unhelpful"
    assert resp.json()["reason"] is None

    rows = db_session.query(QualityFeedback).all()
    assert len(rows) == 1, "同用户同条目应 upsert 只留最新一条"
    assert rows[0].feedback_type.value == "unhelpful"
    assert rows[0].target_id == uuid.UUID(target_id).hex


def test_feedback_kaoyan_news_target(client, auth_headers, db_session):
    news = _make_kaoyan_news(db_session)
    resp = client.post(
        POST_URL,
        headers=auth_headers,
        json={
            "target_type": "kaoyan_news",
            "target_id": str(news.id),
            "feedback_type": "helpful",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["target_type"] == "kaoyan_news"


def test_feedback_rate_limited(client, auth_headers, db_session):
    post = _make_experience_post(db_session)
    target_id = str(post.id)
    payload = {
        "target_type": "experience_post",
        "target_id": target_id,
        "feedback_type": "helpful",
    }
    # 5/minute 限流：前 5 次成功，第 6 次 429
    for _ in range(5):
        assert client.post(POST_URL, headers=auth_headers, json=payload).status_code == 200
    resp = client.post(POST_URL, headers=auth_headers, json=payload)
    assert resp.status_code == 429
