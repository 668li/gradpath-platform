# backend/tests/test_ingestion.py
"""数据真实性接入层（/api/v1/admin/*）测试 — 方案 C 落地实现验证。

覆盖：
- 来源标注 CRUD（t_data_source）：列表/过滤/更新/404/非管理员 403
- 人工触发（POST /ingest）：强制护栏生效 / manual 拒绝 / 未知爬虫 400
- 运行状态查询（GET /ingest/{run_id}）：UUID 字符串契约 / 404
- 人工确认入库（POST /confirm）：PENDING→APPROVED + promote 落业务表 + 来源追溯
  + 409 冲突（重复确认 / run_id 不一致 / source_url 占用）
- 合规红线：无自动入库通道（/ai/orchestrate 已下线 → 404）
"""
import pytest
from datetime import datetime
from hashlib import md5
from sqlalchemy.orm import Session

from app.models.ingestion import DataSourceMeta, ExternalResearchItem, ReviewQueueItem
from app.models.kaoyan_news import KaoyanNews
from app.models.user import User

_RUN_ID = "00000000000000000000000000000000"
_TS = datetime(2026, 8, 12, 8, 0, 0)


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
    source_url: str = "https://yz.chsi.com.cn/2026/kyzs.shtml",
    title: str = "2026 研招网通知",
    content: str = "复试线公布内容",
    external_meta: dict | None = None,
) -> tuple[ExternalResearchItem, ReviewQueueItem]:
    """构造 PENDING 的 t_external_research_item + t_review_queue_item（研招网 kaoyan_news）。"""
    meta = external_meta if external_meta is not None else {
        "summary": "研招网复试线资讯",
        "category": "复试",
        "tags": ["考研"],
        "crawled_at": "2026-08-12T08:00:00Z",
    }
    ext = ExternalResearchItem(
        crawler_name="real_data",
        crawler_run_id=_RUN_ID,
        item_type="kaoyan_news",
        title=title,
        content=content,
        source_url=source_url,
        source_platform="web",
        external_meta=meta,
        credibility="official_verified",
        review_status="PENDING",
    )
    db.add(ext)
    db.flush()
    queue = ReviewQueueItem(
        item_type="external_research",
        ref_item_id=ext.id,
        source_url=source_url,
        review_status="PENDING",
        biz_req_no=f"research:real_data:{md5(source_url.encode()).hexdigest()[:12]}",
    )
    db.add(queue)
    db.commit()
    return ext, queue


# ======================================================================
# 来源标注 CRUD（/api/v1/admin/sources）
# ======================================================================


class TestSources:
    def test_list_sources(self, client, admin_headers, db_session):
        db_session.add(
            DataSourceMeta(
                source_system="yanzhao",
                source_url="https://yz.chsi.com.cn/2026/kyzs.shtml",
                crawled_at=_TS,
                credibility="official_verified",
                verify_count=1,
                review_status="APPROVED",
            )
        )
        db_session.commit()

        resp = client.get("/api/v1/admin/sources", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        item = data["items"][0]
        # source_id 手动映射（≠ 主键 id 语义）
        assert item["source_id"] == 1
        assert item["source_system"] == "yanzhao"
        assert item["credibility"] == "official_verified"
        assert item["verify_count"] == 1
        assert item["review_status"] == "APPROVED"

    def test_list_sources_filter_and_pagination(self, client, admin_headers, db_session):
        for i in range(3):
            db_session.add(
                DataSourceMeta(
                    source_system="yanzhao",
                    source_url=f"https://yz.chsi.com.cn/2026/{i}.shtml",
                    crawled_at=_TS,
                    credibility="model_inferred",
                    verify_count=0,
                    review_status="PENDING",
                )
            )
        db_session.commit()

        resp = client.get(
            "/api/v1/admin/sources?review_status=PENDING&credibility=model_inferred&page=1&page_size=2",
            headers=admin_headers,
        )
        data = resp.json()
        assert data["total"] == 3
        assert len(data["items"]) == 2

    def test_update_source(self, client, admin_headers, db_session):
        db_session.add(
            DataSourceMeta(
                source_system="yanzhao",
                source_url="https://yz.chsi.com.cn/2026/kyzs.shtml",
                crawled_at=_TS,
                credibility="model_inferred",
                verify_count=0,
                review_status="PENDING",
            )
        )
        db_session.commit()

        resp = client.put(
            "/api/v1/admin/sources/1",
            json={"credibility": "official_verified", "review_status": "APPROVED", "verify_count": 2},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["credibility"] == "official_verified"
        assert data["review_status"] == "APPROVED"
        assert data["verify_count"] == 2
        assert data["reviewed_by"] == "admin@test.com"

    def test_update_source_partial(self, client, admin_headers, db_session):
        db_session.add(
            DataSourceMeta(
                source_system="yanzhao",
                source_url="https://yz.chsi.com.cn/2026/kyzs.shtml",
                crawled_at=_TS,
                credibility="official_verified",
                verify_count=1,
                review_status="PENDING",
            )
        )
        db_session.commit()

        resp = client.put(
            "/api/v1/admin/sources/1",
            json={"review_status": "REJECTED"},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["review_status"] == "REJECTED"
        assert data["credibility"] == "official_verified"  # 未更新字段保持

    def test_update_source_missing_404(self, client, admin_headers):
        resp = client.put(
            "/api/v1/admin/sources/9999",
            json={"review_status": "APPROVED"},
            headers=admin_headers,
        )
        assert resp.status_code == 404

    def test_non_admin_forbidden(self, client, db_session):
        client.post(
            "/api/auth/register",
            json={"email": "normal@test.com", "password": "Test1234!", "name": "普通"},
        )
        resp = client.post(
            "/api/auth/login",
            json={"email": "normal@test.com", "password": "Test1234!"},
        )
        headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}
        r = client.get("/api/v1/admin/sources", headers=headers)
        assert r.status_code == 403


# ======================================================================
# 人工触发（POST /ingest）— 强制护栏 + manual 拒绝
# ======================================================================


class TestTriggerIngest:
    def test_trigger_manual_rejected_400(self, client, admin_headers):
        """manual 来源无爬虫可触发 → 400（应走 POST /confirm 直接确认）。"""
        resp = client.post(
            "/api/v1/admin/research/ingest",
            json={"source_system": "manual", "biz_req_no": "MANUAL-001", "url": "https://example.com/a"},
            headers=admin_headers,
        )
        assert resp.status_code == 400
        assert "manual" in resp.json()["detail"]

    def test_trigger_unknown_crawler_400(self, client, admin_headers, monkeypatch):
        """来源系统映射的爬虫未注册 → 400。"""
        import app.services.ingestion_service as svc

        monkeypatch.setattr(svc, "get_crawler", lambda name: None)
        resp = client.post(
            "/api/v1/admin/research/ingest",
            json={"source_system": "yanzhao", "biz_req_no": "YZ-001"},
            headers=admin_headers,
        )
        assert resp.status_code == 400
        assert "未注册" in resp.json()["detail"]

    def test_trigger_applies_guard_and_reports_run(self, client, admin_headers, db_session, monkeypatch):
        """触发 yanzhao → 走 real_data 爬虫，护栏参数强制注入，返回运行状态。"""
        import app.services.ingestion_service as svc
        from app.models.crawler_run import CrawlerRun

        captured: dict = {}

        class _FakeCrawler:
            name = "real_data"
            category = "grad"

            def __init__(self, config=None):
                captured["config"] = config

            def run(self, db=None):
                run_record = CrawlerRun(
                    source_name=self.name,
                    category=self.category,
                    status="success",
                    stored_count=2,
                )
                db.add(run_record)
                db.commit()
                db.refresh(run_record)
                # 1 条 PENDING 待确认（本次运行产物）
                db.add(
                    ExternalResearchItem(
                        crawler_name=self.name,
                        crawler_run_id=str(run_record.id),
                        item_type="kaoyan_news",
                        title="研招网数据",
                        content="x",
                        source_url="https://yz.chsi.com.cn/a/b",
                        source_platform="web",
                        external_meta={"summary": "s", "category": "c", "tags": [], "crawled_at": "2026-08-12T08:00:00Z"},
                        credibility="official_verified",
                        review_status="PENDING",
                    )
                )
                db.commit()
                return {"status": "success", "fetched": 2, "stored": 2, "errors": 0, "duplicates": 0}

        monkeypatch.setattr(svc, "get_crawler", lambda name: _FakeCrawler)

        resp = client.post(
            "/api/v1/admin/research/ingest",
            json={"source_system": "yanzhao", "biz_req_no": "YZ-001", "target_type": "program"},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["source_system"] == "yanzhao"
        assert data["status"] == "success"
        assert data["total_items"] == 2
        assert data["pending_items"] == 1
        # 合规红线：人工触发强制护栏（限量/限速），不随配置放开
        assert captured["config"]["max_pages"] == 1
        assert captured["config"]["max_items"] == 50
        assert captured["config"]["rate_limit"] == 1.0
        # 护栏参数覆盖了配置默认值
        assert captured["config"].get("max_pages", 0) == 1


# ======================================================================
# 运行状态查询（GET /ingest/{run_id}）
# ======================================================================


class TestGetIngestRun:
    def test_get_run_by_uuid_string(self, client, admin_headers, db_session):
        from app.models.crawler_run import CrawlerRun

        run = CrawlerRun(source_name="real_data", category="grad", status="success", stored_count=3)
        db_session.add(run)
        db_session.commit()
        db_session.refresh(run)

        resp = client.get(f"/api/v1/admin/research/ingest/{run.id}", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["run_id"] == str(run.id)
        assert data["status"] == "success"
        assert data["total_items"] == 3

    def test_get_run_missing_404(self, client, admin_headers):
        resp = client.get(
            "/api/v1/admin/research/ingest/11111111-1111-1111-1111-111111111111",
            headers=admin_headers,
        )
        assert resp.status_code == 404

    def test_get_run_invalid_uuid_404(self, client, admin_headers):
        resp = client.get("/api/v1/admin/research/ingest/not-a-uuid", headers=admin_headers)
        assert resp.status_code == 404


# ======================================================================
# 人工确认入库（POST /confirm）
# ======================================================================


class TestConfirmIngest:
    def test_confirm_promotes_kaoyan_news(self, client, admin_headers, db_session):
        ext, queue = _seed_queue_item(db_session)
        resp = client.post(
            "/api/v1/admin/research/confirm",
            json={
                "run_id": _RUN_ID,
                "record_id": ext.id,
                "operator_id": 1,
                "confirmed_fields": {
                    "school": "清华大学",
                    "major": "计算机科学与技术",
                    "scoreline": 340,
                },
                "source_url": "https://yz.chsi.com.cn/2026/kyzs.shtml",
                "source_system": "yanzhao",
                "note": "已核对研招网公告",
            },
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["record_id"] == ext.id
        assert data["run_id"] == _RUN_ID
        assert data["status"] == "approved"
        assert data["confirmed_fields"]["scoreline"] == 340

        # 落业务表：KaoyanNews + 状态回填
        news = db_session.query(KaoyanNews).filter(
            KaoyanNews.source_url == ext.source_url
        ).first()
        assert news is not None
        assert news.status == "approved"
        assert news.category == "复试"

        db_session.refresh(ext)
        db_session.refresh(queue)
        assert ext.review_status == "APPROVED"
        assert queue.review_status == "APPROVED"
        assert queue.reviewed_by == "admin@test.com"
        # 人工确认字段写入 external_meta（来源追溯）
        assert ext.external_meta["confirmed_fields"]["scoreline"] == 340
        assert ext.external_meta["confirm_operator_id"] == 1
        assert ext.external_meta["confirm_note"] == "已核对研招网公告"

        # 来源标注（合规红线：外部数据来源可追溯）+ promote 回填 APPROVED
        ds = db_session.query(DataSourceMeta).filter(
            DataSourceMeta.source_url == ext.source_url
        ).first()
        assert ds is not None
        assert ds.review_status == "APPROVED"
        assert ds.reviewed_by == "admin@test.com"

    def test_confirm_duplicate_409(self, client, admin_headers, db_session):
        ext, _ = _seed_queue_item(db_session)
        payload = {
            "run_id": _RUN_ID,
            "record_id": ext.id,
            "operator_id": 1,
            "confirmed_fields": {},
            "source_url": "https://yz.chsi.com.cn/2026/kyzs.shtml",
            "source_system": "yanzhao",
        }
        assert client.post("/api/v1/admin/research/confirm", json=payload, headers=admin_headers).status_code == 200
        # 重复确认 → 409
        resp = client.post("/api/v1/admin/research/confirm", json=payload, headers=admin_headers)
        assert resp.status_code == 409

    def test_confirm_run_id_mismatch_409(self, client, admin_headers, db_session):
        ext, _ = _seed_queue_item(db_session)
        resp = client.post(
            "/api/v1/admin/research/confirm",
            json={
                "run_id": "99999999-9999-9999-9999-999999999999",
                "record_id": ext.id,
                "operator_id": 1,
                "confirmed_fields": {},
                "source_url": "https://yz.chsi.com.cn/2026/kyzs.shtml",
                "source_system": "yanzhao",
            },
            headers=admin_headers,
        )
        assert resp.status_code == 409

    def test_confirm_missing_record_404(self, client, admin_headers):
        resp = client.post(
            "/api/v1/admin/research/confirm",
            json={
                "run_id": _RUN_ID,
                "record_id": 99999,
                "operator_id": 1,
                "confirmed_fields": {},
                "source_url": "https://yz.chsi.com.cn/2026/kyzs.shtml",
                "source_system": "yanzhao",
            },
            headers=admin_headers,
        )
        assert resp.status_code == 404

    def test_confirm_source_url_conflict_409(self, client, admin_headers, db_session):
        _, _ = _seed_queue_item(db_session)  # 占用 source_url A
        ext2, _ = _seed_queue_item(
            db_session,
            source_url="https://yz.chsi.com.cn/2026/other.shtml",
            title="另一条待确认",
        )
        # 尝试把第二条的来源 URL 改成第一条占用的 → 409
        resp = client.post(
            "/api/v1/admin/research/confirm",
            json={
                "run_id": _RUN_ID,
                "record_id": ext2.id,
                "operator_id": 1,
                "confirmed_fields": {},
                "source_url": "https://yz.chsi.com.cn/2026/kyzs.shtml",
                "source_system": "yanzhao",
            },
            headers=admin_headers,
        )
        assert resp.status_code == 409
        assert "占用" in resp.json()["detail"]

    def test_confirm_non_admin_forbidden(self, client, db_session):
        client.post(
            "/api/auth/register",
            json={"email": "normal2@test.com", "password": "Test1234!", "name": "普通"},
        )
        resp = client.post(
            "/api/auth/login",
            json={"email": "normal2@test.com", "password": "Test1234!"},
        )
        headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}
        r = client.post(
            "/api/v1/admin/research/confirm",
            json={
                "run_id": _RUN_ID,
                "record_id": 1,
                "operator_id": 1,
                "confirmed_fields": {},
                "source_url": "https://yz.chsi.com.cn/2026/kyzs.shtml",
                "source_system": "yanzhao",
            },
            headers=headers,
        )
        assert r.status_code == 403


# ======================================================================
# 合规红线：无自动入库通道
# ======================================================================


class TestNoAutoIngest:
    def test_orchestrate_endpoint_removed_404(self, client):
        """统一编排入口已下线：POST /api/v1/ai/orchestrate → 404（不自动入库）。"""
        resp = client.post(
            "/api/v1/ai/orchestrate",
            json={"service_name": "grad_intel_service", "prompt": "分析一下"},
        )
        assert resp.status_code == 404

    def test_governance_status_still_served(self, client, admin_headers):
        """治理总览保留（真实动态检测），不受 orchestrate 下线影响。"""
        resp = client.get("/api/v1/admin/ai/governance-status", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert len(data["services"]) == data["total"]
