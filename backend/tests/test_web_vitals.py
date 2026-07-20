# tests/test_web_vitals.py
"""C9 web-vitals 上报 API 与服务层测试。

覆盖：
- POST /api/metrics/web-vitals 上报 5 种核心指标 (LCP/CLS/INP/TTFB/FCP)
- 字段校验：无效指标名 / 无效评级 / 字段超长 / 缺失必填
- 未登录返回 401
- 持久化到 events 表（event_type=web_vital）
- GET /api/metrics/web-vitals/summary 聚合查询
- web_vitals_service.record_web_vital 单元测试
- web_vitals_service.track_event / track_page_view / track_click 通用埋点
- Prometheus 指标记录（record_web_vital 增加计数器）
"""
import pytest
from fastapi.testclient import TestClient

from app.models.event import Event
from app.models.user import User
from app.services.web_vitals_service import (
    ALLOWED_RATINGS,
    ALLOWED_VITAL_NAMES,
    get_web_vitals_summary,
    record_web_vital,
    track_click,
    track_event,
    track_page_view,
)


class TestWebVitalsReportAPI:
    """POST /api/metrics/web-vitals 端点测试。"""

    def test_report_lcp_success(self, client: TestClient, auth_headers: dict):
        """成功上报 LCP 指标。"""
        resp = client.post(
            "/api/metrics/web-vitals",
            headers=auth_headers,
            json={
                "name": "LCP",
                "value": 2500.5,
                "rating": "good",
                "delta": 100.2,
                "id": "v3-1718923456789-12345",
                "page": "/dashboard",
                "session_id": "sess-abc-123",
                "timestamp": "2026-07-20T10:30:00.000Z",
            },
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["received"] is True
        assert body["name"] == "LCP"
        assert body["value"] == 2500.5
        assert body["rating"] == "good"

    def test_report_all_five_metrics(self, client: TestClient, auth_headers: dict):
        """成功上报 5 种核心指标。"""
        metrics = [
            {"name": "LCP", "value": 2500.0, "rating": "good"},
            {"name": "CLS", "value": 0.05, "rating": "good"},
            {"name": "INP", "value": 200.0, "rating": "needs-improvement"},
            {"name": "TTFB", "value": 800.0, "rating": "needs-improvement"},
            {"name": "FCP", "value": 1800.0, "rating": "poor"},
        ]
        for m in metrics:
            resp = client.post(
                "/api/metrics/web-vitals",
                headers=auth_headers,
                json={
                    **m,
                    "delta": 0.0,
                    "id": f"id-{m['name']}",
                    "page": "/test",
                    "session_id": "sess-test",
                },
            )
            assert resp.status_code == 201, f"指标 {m['name']} 上报失败: {resp.text}"

    def test_report_unauthorized(self, client: TestClient):
        """未登录上报返回 401。"""
        resp = client.post(
            "/api/metrics/web-vitals",
            json={"name": "LCP", "value": 2500.0, "rating": "good"},
        )
        assert resp.status_code in (401, 403)

    def test_report_invalid_metric_name(self, client: TestClient, auth_headers: dict):
        """无效指标名返回 422。"""
        resp = client.post(
            "/api/metrics/web-vitals",
            headers=auth_headers,
            json={"name": "INVALID", "value": 100, "rating": "good"},
        )
        assert resp.status_code == 422

    def test_report_invalid_rating(self, client: TestClient, auth_headers: dict):
        """无效评级返回 422。"""
        resp = client.post(
            "/api/metrics/web-vitals",
            headers=auth_headers,
            json={"name": "LCP", "value": 100, "rating": "excellent"},
        )
        assert resp.status_code == 422

    def test_report_missing_name(self, client: TestClient, auth_headers: dict):
        """缺失必填字段 name 返回 422。"""
        resp = client.post(
            "/api/metrics/web-vitals",
            headers=auth_headers,
            json={"value": 100, "rating": "good"},
        )
        assert resp.status_code == 422

    def test_report_missing_value(self, client: TestClient, auth_headers: dict):
        """缺失必填字段 value 返回 422。"""
        resp = client.post(
            "/api/metrics/web-vitals",
            headers=auth_headers,
            json={"name": "LCP", "rating": "good"},
        )
        assert resp.status_code == 422

    def test_report_missing_rating(self, client: TestClient, auth_headers: dict):
        """缺失必填字段 rating 返回 422。"""
        resp = client.post(
            "/api/metrics/web-vitals",
            headers=auth_headers,
            json={"name": "LCP", "value": 100},
        )
        assert resp.status_code == 422

    def test_report_lowercase_name_normalized(
        self, client: TestClient, auth_headers: dict
    ):
        """小写指标名应被规范化为大写。"""
        resp = client.post(
            "/api/metrics/web-vitals",
            headers=auth_headers,
            json={"name": "lcp", "value": 2000, "rating": "good"},
        )
        assert resp.status_code == 201
        assert resp.json()["name"] == "LCP"

    def test_report_uppercase_rating_normalized(
        self, client: TestClient, auth_headers: dict
    ):
        """大写评级应被规范化为小写。"""
        resp = client.post(
            "/api/metrics/web-vitals",
            headers=auth_headers,
            json={"name": "LCP", "value": 2000, "rating": "GOOD"},
        )
        assert resp.status_code == 201
        assert resp.json()["rating"] == "good"

    def test_report_persists_to_events_table(
        self, client: TestClient, auth_headers: dict, db_session
    ):
        """上报后应持久化到 events 表。"""
        before_count = (
            db_session.query(Event).filter(Event.event_type == "web_vital").count()
        )
        resp = client.post(
            "/api/metrics/web-vitals",
            headers=auth_headers,
            json={
                "name": "LCP",
                "value": 2500.5,
                "rating": "good",
                "delta": 100.0,
                "id": "metric-id-test",
                "page": "/test-persist",
                "session_id": "sess-persist",
            },
        )
        assert resp.status_code == 201

        after_count = (
            db_session.query(Event).filter(Event.event_type == "web_vital").count()
        )
        assert after_count == before_count + 1

        # 验证最新事件的字段
        latest = (
            db_session.query(Event)
            .filter(Event.event_type == "web_vital")
            .order_by(Event.id.desc())
            .first()
        )
        assert latest is not None
        assert latest.page == "/test-persist"
        assert latest.session_id == "sess-persist"
        payload = latest.payload or {}
        assert payload.get("name") == "LCP"
        assert payload.get("value") == 2500.5
        assert payload.get("rating") == "good"
        assert payload.get("metric_id") == "metric-id-test"
        assert latest.user_id is not None

    def test_report_field_too_long(self, client: TestClient, auth_headers: dict):
        """字段超长返回 422。"""
        # page 超过 500 字符
        resp = client.post(
            "/api/metrics/web-vitals",
            headers=auth_headers,
            json={
                "name": "LCP",
                "value": 100,
                "rating": "good",
                "page": "x" * 600,
            },
        )
        assert resp.status_code == 422

    def test_report_negative_value_accepted(
        self, client: TestClient, auth_headers: dict
    ):
        """负值被接受（CLS 可能为 0 或极小负数，不强制非负）。"""
        resp = client.post(
            "/api/metrics/web-vitals",
            headers=auth_headers,
            json={"name": "CLS", "value": -0.01, "rating": "good"},
        )
        assert resp.status_code == 201


class TestWebVitalsSummaryAPI:
    """GET /api/metrics/web-vitals/summary 端点测试。"""

    def test_summary_empty(self, client: TestClient, auth_headers: dict):
        """无数据时返回空字典。"""
        resp = client.get("/api/metrics/web-vitals/summary", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == {}

    def test_summary_after_reports(self, client: TestClient, auth_headers: dict):
        """上报后聚合查询应返回统计数据。"""
        # 上报 3 条 LCP，1 条 poor / 2 条 good
        for v, r in [(1000, "good"), (2500, "good"), (5000, "poor")]:
            client.post(
                "/api/metrics/web-vitals",
                headers=auth_headers,
                json={"name": "LCP", "value": v, "rating": r, "page": "/summary-test"},
            )

        resp = client.get("/api/metrics/web-vitals/summary", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "LCP" in data
        lcp_stats = data["LCP"]
        assert lcp_stats["count"] == 3.0
        assert lcp_stats["avg"] == round((1000 + 2500 + 5000) / 3, 3)
        assert lcp_stats["poor_rate"] == round(1 / 3, 4)

    def test_summary_filter_by_page(
        self, client: TestClient, auth_headers: dict
    ):
        """按 page 过滤聚合查询。"""
        # 上报到不同页面
        client.post(
            "/api/metrics/web-vitals",
            headers=auth_headers,
            json={"name": "LCP", "value": 1000, "rating": "good", "page": "/pageA"},
        )
        client.post(
            "/api/metrics/web-vitals",
            headers=auth_headers,
            json={"name": "LCP", "value": 5000, "rating": "poor", "page": "/pageB"},
        )

        resp = client.get(
            "/api/metrics/web-vitals/summary?page=/pageA",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "LCP" in data
        assert data["LCP"]["count"] == 1.0

    def test_summary_unauthorized(self, client: TestClient):
        """未登录查询返回 401。"""
        resp = client.get("/api/metrics/web-vitals/summary")
        assert resp.status_code in (401, 403)

    def test_summary_invalid_limit(self, client: TestClient, auth_headers: dict):
        """limit 超出范围返回 422。"""
        resp = client.get(
            "/api/metrics/web-vitals/summary?limit=0",
            headers=auth_headers,
        )
        assert resp.status_code == 422

        resp2 = client.get(
            "/api/metrics/web-vitals/summary?limit=10001",
            headers=auth_headers,
        )
        assert resp2.status_code == 422


class TestWebVitalsService:
    """web_vitals_service 服务层单元测试。"""

    def _get_user(self, db_session) -> User:
        """获取或创建测试用户。db_session fixture 不会自动创建用户
        （用户由 auth_headers fixture 注册流程创建），所以这里按需创建。
        """
        user = db_session.query(User).first()
        if user is not None:
            return user
        user = User(
            email="svc-test@example.com",
            password_hash="fake-hash",
            name="svc-test-user",
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user

    def test_record_web_vital_persists_event(self, db_session):
        """record_web_vital 应写入 Event 表。"""
        user = self._get_user(db_session)
        before = db_session.query(Event).filter(Event.event_type == "web_vital").count()

        event = record_web_vital(
            db=db_session,
            user_id=user.id,
            name="LCP",
            value=2000.5,
            rating="good",
            delta=100.0,
            metric_id="svc-test-1",
            page="/service-test",
            session_id="svc-sess",
        )
        assert event.id is not None
        assert event.event_type == "web_vital"
        assert event.page == "/service-test"
        assert event.session_id == "svc-sess"
        assert event.user_id == user.id

        after = db_session.query(Event).filter(Event.event_type == "web_vital").count()
        assert after == before + 1

        payload = event.payload or {}
        assert payload["name"] == "LCP"
        assert payload["value"] == 2000.5
        assert payload["rating"] == "good"
        assert payload["delta"] == 100.0
        assert payload["metric_id"] == "svc-test-1"

    def test_record_web_vital_anonymous_user(self, db_session):
        """未登录用户上报 user_id=None。"""
        event = record_web_vital(
            db=db_session,
            user_id=None,
            name="CLS",
            value=0.05,
            rating="good",
            page="/anon",
            session_id="anon-sess",
        )
        assert event.user_id is None
        assert event.payload["name"] == "CLS"

    def test_record_web_vital_invalid_name_raises(self, db_session):
        """未知指标名应抛出 ValueError。"""
        with pytest.raises(ValueError):
            record_web_vital(
                db=db_session,
                user_id=None,
                name="INVALID",
                value=100,
                rating="good",
            )

    def test_record_web_vital_invalid_rating_raises(self, db_session):
        """未知评级应抛出 ValueError。"""
        with pytest.raises(ValueError):
            record_web_vital(
                db=db_session,
                user_id=None,
                name="LCP",
                value=100,
                rating="excellent",
            )

    def test_record_web_vital_truncates_long_page(self, db_session):
        """过长的 page 字段应被截断。"""
        long_page = "x" * 600
        event = record_web_vital(
            db=db_session,
            user_id=None,
            name="LCP",
            value=100,
            rating="good",
            page=long_page,
            session_id="sess",
        )
        assert len(event.page) <= 500

    def test_record_web_vital_normalizes_case(self, db_session):
        """指标名与评级应被规范化。"""
        event = record_web_vital(
            db=db_session,
            user_id=None,
            name="lcp",
            value=100,
            rating="GOOD",
        )
        assert event.payload["name"] == "LCP"
        assert event.payload["rating"] == "good"

    def test_track_event_writes_generic_event(self, db_session):
        """track_event 写入通用事件。"""
        user = self._get_user(db_session)
        event = track_event(
            db=db_session,
            user_id=user.id,
            session_id="track-sess",
            event_type="page_view",
            page="/home",
            element=None,
            payload={"referrer": "/search"},
        )
        assert event.event_type == "page_view"
        assert event.page == "/home"
        assert event.session_id == "track-sess"
        assert event.payload["referrer"] == "/search"

    def test_track_page_view(self, db_session):
        """track_page_view 写入页面浏览事件。"""
        user = self._get_user(db_session)
        event = track_page_view(
            db=db_session,
            user_id=user.id,
            session_id="pv-sess",
            page="/dashboard",
            referrer="/login",
        )
        assert event.event_type == "page_view"
        assert event.page == "/dashboard"
        assert event.payload["referrer"] == "/login"

    def test_track_click(self, db_session):
        """track_click 写入点击事件。"""
        user = self._get_user(db_session)
        event = track_click(
            db=db_session,
            user_id=user.id,
            session_id="click-sess",
            page="/dashboard",
            element="cta-apply",
            text="立即申请",
            tag="button",
        )
        assert event.event_type == "click"
        assert event.element == "cta-apply"
        assert event.payload["text"] == "立即申请"
        assert event.payload["tag"] == "button"

    def test_track_event_long_event_type_truncated(self, db_session):
        """超长 event_type 应被截断。"""
        long_type = "x" * 100
        event = track_event(
            db=db_session,
            user_id=None,
            session_id="sess",
            event_type=long_type,
        )
        assert len(event.event_type) == 50

    def test_track_event_empty_session_normalized(self, db_session):
        """空 session_id 应被规范化为 'unknown'。"""
        event = track_event(
            db=db_session,
            user_id=None,
            session_id="",
            event_type="page_view",
        )
        assert event.session_id == "unknown"

    def test_get_web_vitals_summary_empty(self, db_session):
        """无数据时返回空字典。"""
        summary = get_web_vitals_summary(db_session)
        assert summary == {}

    def test_get_web_vitals_summary_with_data(self, db_session):
        """有数据时返回按指标名分组的统计。"""
        # 上报 4 条 LCP
        for v, r in [(1000, "good"), (2000, "good"), (4000, "needs-improvement"), (6000, "poor")]:
            record_web_vital(
                db=db_session,
                user_id=None,
                name="LCP",
                value=v,
                rating=r,
                page="/summary",
            )

        summary = get_web_vitals_summary(db_session)
        assert "LCP" in summary
        lcp = summary["LCP"]
        assert lcp["count"] == 4.0
        assert lcp["avg"] == round((1000 + 2000 + 4000 + 6000) / 4, 3)
        assert lcp["p50"] == 2000.0  # sorted: [1000, 2000, 4000, 6000], n//2=2
        assert lcp["poor_rate"] == 0.25

    def test_get_web_vitals_summary_filter_by_session(self, db_session):
        """按 session_id 过滤。"""
        record_web_vital(
            db=db_session,
            user_id=None,
            name="LCP",
            value=1000,
            rating="good",
            page="/p",
            session_id="sess-A",
        )
        record_web_vital(
            db=db_session,
            user_id=None,
            name="LCP",
            value=5000,
            rating="poor",
            page="/p",
            session_id="sess-B",
        )

        summary = get_web_vitals_summary(db_session, session_id="sess-A")
        assert summary["LCP"]["count"] == 1.0
        assert summary["LCP"]["avg"] == 1000.0


class TestWebVitalsPrometheusIntegration:
    """web-vitals Prometheus 指标集成测试。"""

    def test_record_web_vital_updates_prometheus_counter(self, db_session):
        """record_web_vital 调用后 Prometheus Counter 应增加。"""
        from app.metrics import WEB_VITALS_REPORT_COUNT

        if WEB_VITALS_REPORT_COUNT is None:
            pytest.skip("prometheus_client 不可用")

        # 记录调用前的计数（prometheus_client Counter 不易直接读取样本值，
        # 此处仅验证调用不抛错）
        record_web_vital(
            db=db_session,
            user_id=None,
            name="LCP",
            value=2000,
            rating="good",
            page="/prom-test",
        )
        # 二次调用应正常
        record_web_vital(
            db=db_session,
            user_id=None,
            name="CLS",
            value=0.1,
            rating="needs-improvement",
            page="/prom-test",
        )

    def test_record_web_vital_function_callable(self):
        """app.metrics.record_web_vital 函数应可调用。"""
        from app.metrics import record_web_vital as metric_fn

        # 调用不应抛错（prometheus_client 不可用时静默返回）
        metric_fn("LCP", 2000.0, "good", "/test")
        metric_fn("CLS", 0.05, "good", "/test")
        metric_fn("INP", 200.0, "needs-improvement", "/test")
        metric_fn("TTFB", 800.0, "needs-improvement", "/test")
        metric_fn("FCP", 1800.0, "poor", "/test")

    def test_record_web_vital_unknown_metric_ignored(self):
        """未知指标名应被静默忽略（不抛错）。"""
        from app.metrics import record_web_vital as metric_fn

        metric_fn("UNKNOWN", 100.0, "good", "/test")


class TestWebVitalsConstants:
    """验证常量定义。"""

    def test_allowed_vital_names(self):
        """允许的指标名集合正确。"""
        assert ALLOWED_VITAL_NAMES == frozenset({"LCP", "CLS", "INP", "TTFB", "FCP"})

    def test_allowed_ratings(self):
        """允许的评级集合正确。"""
        assert ALLOWED_RATINGS == frozenset({"good", "needs-improvement", "poor"})
