# backend/tests/test_research_queue.py
"""审核队列（t_review_queue_item）测试 — 统一走新队列后的审核状态机 + promote 落库幂等。

覆盖（P1 修理链路）：
- 待审核列表（JOIN 外部调研条目带出标题/可信度）
- approve：PENDING→APPROVED + 落业务表（ExperiencePost/KaoyanNews）+ 回填 ext 状态
- 重复审核 409 / 不存在 404 / 非管理员 403
- reject / duplicate 状态转移与回填
- promote 幂等：同 source_url 二次通过不重复落业务表
"""
import pytest
from hashlib import md5
from sqlalchemy.orm import Session

from app.models.experience_post import ExperiencePost
from app.models.ingestion import ExternalResearchItem, ReviewQueueItem
from app.models.kaoyan_news import KaoyanNews
from app.models.user import User


@pytest.fixture
def admin_headers(client, db_session):
    from app.core.security import hash_password

    admin = User(
        email="admin@test.com",
        password_hash=hash_password("Admin1234!"),
        name="管理员",
        is_admin=True,
    )
    db_session.add(admin)
    db_session.commit()
    resp = client.post(
        "/api/auth/login",
        json={"email": "admin@test.com", "password": "Admin1234!"},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _seed_queue_item(
    db: Session,
    *,
    item_type: str = "experience_post",
    source_url: str = "https://example.com/posts/1",
    title: str = "考研复试经验分享",
    content: str = "复试流程与注意事项的详细记录",
    source_platform: str = "bilibili",
    external_meta: dict | None = None,
) -> tuple[ExternalResearchItem, ReviewQueueItem]:
    """构造 PENDING 的 t_external_research_item + t_review_queue_item。"""
    meta = external_meta if external_meta is not None else {
        "author": "UP主",
        "view_count": 120,
        "like_count": 8,
        "tags": ["复试"],
    }
    ext = ExternalResearchItem(
        crawler_name="bilibili_research",
        crawler_run_id="00000000000000000000000000000000",
        item_type=item_type,
        title=title,
        content=content,
        source_url=source_url,
        source_platform=source_platform,
        external_meta=meta,
        credibility="model_inferred",
        review_status="PENDING",
    )
    db.add(ext)
    db.flush()
    queue = ReviewQueueItem(
        item_type="external_research",
        ref_item_id=ext.id,
        source_url=source_url,
        review_status="PENDING",
        biz_req_no=f"research:bilibili_research:{md5(source_url.encode()).hexdigest()[:12]}",
    )
    db.add(queue)
    db.commit()
    return ext, queue


class TestListPending:
    def test_list_pending_joins_ext_item(self, client, admin_headers, db_session):
        _seed_queue_item(db_session)
        resp = client.get("/api/admin/research-queue/pending", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        item = data["items"][0]
        assert item["review_status"] == "PENDING"
        assert item["title"] == "考研复试经验分享"
        assert item["credibility"] == "model_inferred"
        assert item["source_platform"] == "bilibili"
        assert item["content"] == "复试流程与注意事项的详细记录"

    def test_list_filter_by_status(self, client, admin_headers, db_session):
        _, queue = _seed_queue_item(db_session)
        queue.review_status = "APPROVED"
        db_session.commit()
        resp = client.get(
            "/api/admin/research-queue/pending?review_status=APPROVED",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["total"] == 1
        # 默认只查 PENDING → 0
        resp2 = client.get("/api/admin/research-queue/pending", headers=admin_headers)
        assert resp2.json()["total"] == 0

    def test_pagination(self, client, admin_headers, db_session):
        for i in range(3):
            _seed_queue_item(
                db_session,
                source_url=f"https://example.com/posts/{i}",
                title=f"经验贴{i}",
            )
        resp = client.get(
            "/api/admin/research-queue/pending?page=1&page_size=2",
            headers=admin_headers,
        )
        data = resp.json()
        assert data["total"] == 3
        assert len(data["items"]) == 2


class TestApprove:
    def test_approve_promotes_experience_post(self, client, admin_headers, db_session):
        ext, queue = _seed_queue_item(db_session)
        resp = client.post(
            f"/api/admin/research-queue/{queue.id}/approve",
            json={},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["review_status"] == "APPROVED"
        assert data["promoted"] == 1

        # 业务表落库：ExperiencePost 一条 + 系统用户确保
        post = db_session.query(ExperiencePost).filter(
            ExperiencePost.source_url == ext.source_url
        ).first()
        assert post is not None
        assert post.status == "approved"
        assert post.source_platform == "bilibili"

        # 回填：ext + 队列状态
        db_session.refresh(ext)
        db_session.refresh(queue)
        assert ext.review_status == "APPROVED"
        assert queue.review_status == "APPROVED"
        assert queue.reviewed_by == "admin@test.com"

    def test_approve_promotes_kaoyan_news(self, client, admin_headers, db_session):
        ext, queue = _seed_queue_item(
            db_session,
            item_type="kaoyan_news",
            source_platform="rss",
            source_url="https://news.example.com/2026/08/12",
            title="2026 考研复试线公布",
            content="各院校陆续公布复试分数线",
            external_meta={
                "summary": "复试线资讯",
                "category": "复试",
                "tags": ["考研"],
                "crawled_at": "2026-08-12T08:00:00Z",
            },
        )
        resp = client.post(
            f"/api/admin/research-queue/{queue.id}/approve",
            json={},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["promoted"] == 1
        news = db_session.query(KaoyanNews).filter(
            KaoyanNews.source_url == ext.source_url
        ).first()
        assert news is not None
        assert news.status == "approved"
        assert news.category == "复试"

    def test_approve_duplicate_conflict_409(self, client, admin_headers, db_session):
        _, queue = _seed_queue_item(db_session)
        # 第一次通过
        assert (
            client.post(
                f"/api/admin/research-queue/{queue.id}/approve",
                json={},
                headers=admin_headers,
            ).status_code
            == 200
        )
        # 重复审核 → 409
        resp = client.post(
            f"/api/admin/research-queue/{queue.id}/approve",
            json={},
            headers=admin_headers,
        )
        assert resp.status_code == 409

    def test_approve_missing_queue_404(self, client, admin_headers):
        resp = client.post(
            "/api/admin/research-queue/99999/approve",
            json={},
            headers=admin_headers,
        )
        assert resp.status_code == 404

    def test_non_admin_forbidden(self, client):
        client.post(
            "/api/auth/register",
            json={"email": "normal@test.com", "password": "Test1234!", "name": "普通"},
        )
        resp = client.post(
            "/api/auth/login",
            json={"email": "normal@test.com", "password": "Test1234!"},
        )
        headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}
        r = client.get("/api/admin/research-queue/pending", headers=headers)
        assert r.status_code == 403


class TestPromotePurity(TestApprove):
    """Phase G：approve 落库时注入质量分/反软广/结构化元信息。"""

    def test_experience_post_injects_quality_and_promo(self, client, admin_headers, db_session):
        """含引流词的经验贴 → 标注软广（不下架）+ 质量分 + 结构化 meta。"""
        ext, queue = _seed_queue_item(
            db_session,
            source_url="https://example.com/posts/promo1",
            title="408 计算机考研上岸经验（附领资料）",
            content="我加微信领资料，一战考了 380 分上岸，刷题笔记分享",
            external_meta={
                "author": "UP主",
                "view_count": 50000,
                "like_count": 300,
                "tags": ["408", "上岸"],
            },
        )
        resp = client.post(
            f"/api/admin/research-queue/{queue.id}/approve",
            json={},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["promoted"] == 1

        post = db_session.query(ExperiencePost).filter(
            ExperiencePost.source_url == ext.source_url
        ).first()
        assert post is not None
        # 反软广：命中引流词 → 标注但不下架
        assert post.is_promotion is True
        assert post.promotion_confidence > 0
        assert post.promotion_reason.startswith("疑似软广:")
        # 质量分：规则打分器注入（0-100 + A-D）
        assert 0 <= post.quality_score <= 100
        assert post.quality_grade in ("A", "B", "C", "D")
        # 结构化 meta：学科/阶段/院校/目标分
        meta = post.structured_meta or {}
        assert meta.get("subject") is not None
        assert meta.get("target_score") == 380

    def test_clean_experience_post_not_flagged(self, client, admin_headers, db_session):
        """无引流词经验贴 → 不标注，仍有质量分。"""
        ext, queue = _seed_queue_item(
            db_session,
            source_url="https://example.com/posts/clean1",
            title="408 一战上岸北京理工大学经验",
            content="我每天刷 4 小时真题，错题整理成笔记反复复盘，最终初试考了 380 分" * 20,
            external_meta={
                "author": "UP主",
                "view_count": 30000,
                "like_count": 500,
                "tags": ["408", "北京理工大学"],
            },
        )
        client.post(
            f"/api/admin/research-queue/{queue.id}/approve",
            json={},
            headers=admin_headers,
        )
        post = db_session.query(ExperiencePost).filter(
            ExperiencePost.source_url == ext.source_url
        ).first()
        assert post.is_promotion is False
        assert post.promotion_confidence == 0.0
        assert post.quality_grade == "A"
        assert (post.structured_meta or {}).get("school") == "北京理工大学"

    def test_kaoyan_news_injects_structured_meta(self, client, admin_headers, db_session):
        """资讯 approve → 注入 structured_meta（招生人数/科目/参考书）决策数据卡。"""
        ext, queue = _seed_queue_item(
            db_session,
            item_type="kaoyan_news",
            source_platform="rss",
            source_url="https://news.example.com/2026/08/zhang",
            title="2026年XX大学计算机考研招生简章",
            content="计算机学院拟招收 120 人。初试科目：①101思想政治理论②201英语一"
                    "③301数学一④408计算机学科专业基础。参考书：《数据结构（C语言版）》。",
            external_meta={
                "summary": "招生简章",
                "category": "招生简章",
                "tags": ["考研"],
                "crawled_at": "2026-08-12T08:00:00Z",
            },
        )
        client.post(
            f"/api/admin/research-queue/{queue.id}/approve",
            json={},
            headers=admin_headers,
        )
        news = db_session.query(KaoyanNews).filter(
            KaoyanNews.source_url == ext.source_url
        ).first()
        assert news is not None
        meta = news.structured_meta or {}
        assert meta.get("enrollment_count") == 120
        assert "思想政治理论" in meta.get("exam_subjects", [])
        assert "数据结构（C语言版）" in meta.get("reference_books", [])


class TestReject:
    def test_reject_with_reason(self, client, admin_headers, db_session):
        _, queue = _seed_queue_item(db_session)
        resp = client.post(
            f"/api/admin/research-queue/{queue.id}/reject",
            json={"reject_reason": "内容与考研无关"},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["review_status"] == "REJECTED"
        db_session.refresh(queue)
        assert queue.reject_reason == "内容与考研无关"
        assert queue.reviewed_by == "admin@test.com"

    def test_reject_then_approve_409(self, client, admin_headers, db_session):
        _, queue = _seed_queue_item(db_session)
        client.post(
            f"/api/admin/research-queue/{queue.id}/reject",
            json={},
            headers=admin_headers,
        )
        resp = client.post(
            f"/api/admin/research-queue/{queue.id}/approve",
            json={},
            headers=admin_headers,
        )
        assert resp.status_code == 409


class TestDuplicate:
    def test_duplicate_marking(self, client, admin_headers, db_session):
        ext, queue = _seed_queue_item(db_session)
        resp = client.post(
            f"/api/admin/research-queue/{queue.id}/duplicate",
            json={"duplicate_of": "https://example.com/posts/0"},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["review_status"] == "DUPLICATED"
        db_session.refresh(ext)
        assert ext.review_status == "DUPLICATED"
        # 标记重复不落业务表
        assert (
            db_session.query(ExperiencePost)
            .filter(ExperiencePost.source_url == ext.source_url)
            .first()
            is None
        )


class TestPromoteIdempotency:
    def test_promote_skips_existing_source_url(self, client, admin_headers, db_session):
        # 业务表已存在同 URL 经验贴 → 通过时 promote 跳过，不重复落库
        from app.crawlers.research.transformer import SYSTEM_USER_ID

        db_session.add(
            ExperiencePost(
                user_id=SYSTEM_USER_ID,
                title="已存在的经验贴",
                summary="旧",
                content="旧内容",
                tags=[],
                category="general",
                source_platform="bilibili",
                source_url="https://example.com/posts/1",
                status="approved",
            )
        )
        db_session.commit()

        _, queue = _seed_queue_item(db_session)
        resp = client.post(
            f"/api/admin/research-queue/{queue.id}/approve",
            json={},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["promoted"] == 0
        # 仍只有 1 条
        assert (
            db_session.query(ExperiencePost)
            .filter(ExperiencePost.source_url == "https://example.com/posts/1")
            .count()
            == 1
        )


class TestCredibilityInference:
    """P2：credibility 分级规则 — 官方域名/社区平台/其余三级。"""

    def test_official_domain(self, db_session):
        """官方域名（含子域）→ official_verified。"""
        from app.services.research_ingestion import _infer_credibility, store_research_items

        assert _infer_credibility("https://yz.chsi.com.cn/2026/kyzc.shtml", "web") == "official_verified"
        assert _infer_credibility("https://kaoyan.xxx.edu.cn/news/1", "web") == "official_verified"
        assert _infer_credibility("https://www.gov.cn/zhengce/2026.htm", "web") == "official_verified"

        result = store_research_items(
            db_session,
            crawler_name="web_article_research",
            item_type="kaoyan_news",
            items=[{"title": "研招网通知", "content": "x", "source_url": "https://yz.chsi.com.cn/a/b"}],
            source_platform="web",
            run_id="00000000000000000000000000000000",
        )
        assert result["inserted"] == 1
        ext = db_session.query(ExternalResearchItem).filter(
            ExternalResearchItem.source_url == "https://yz.chsi.com.cn/a/b"
        ).one()
        assert ext.credibility == "official_verified"

    def test_community_platform(self, db_session):
        """社区平台（platform 名或 URL 域名命中）→ user_reported。"""
        from app.services.research_ingestion import _infer_credibility, store_research_items

        assert _infer_credibility("https://b23.tv/av123", "bilibili") == "user_reported"
        assert _infer_credibility("https://www.v2ex.com/t/1", "web") == "user_reported"
        assert _infer_credibility("https://github.com/user/repo", "web") == "user_reported"
        assert _infer_credibility("https://www.zhihu.com/question/1", "web") == "user_reported"

        result = store_research_items(
            db_session,
            crawler_name="bilibili_research",
            item_type="experience_post",
            items=[{"title": "UP主经验", "content": "x", "source_url": "https://b23.tv/av123"}],
            source_platform="bilibili",
            run_id="00000000000000000000000000000000",
        )
        assert result["inserted"] == 1
        ext = db_session.query(ExternalResearchItem).filter(
            ExternalResearchItem.source_url == "https://b23.tv/av123"
        ).one()
        assert ext.credibility == "user_reported"

    def test_other_falls_back_to_model_inferred(self):
        """非官方非社区 → model_inferred。"""
        from app.services.research_ingestion import _infer_credibility

        assert _infer_credibility("https://example.com/posts/1", "web") == "model_inferred"
        assert _infer_credibility("https://news.ycombinator.com/item?id=1", "rss") == "model_inferred"
