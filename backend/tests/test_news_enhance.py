# backend/tests/test_news_enhance.py
"""考研资讯 LLM 增强（Phase C2）测试 — 解析/清洗/降级 + 审核落库提纯字段。

覆盖：
- _parse_llm_json：markdown 围栏 / 前后缀噪音 / 非法 JSON
- _sanitize_llm_dates：标签白名单 / 日期格式校验 / 区间 end_date 校验
- enhance_news_item：成功回填（mock AIOrchestrator）/ 失败降级保留规则版
- schedule_news_enhancement：开发环境（memory broker）安全跳过
- 审核 approve → KaoyanNews 落库即带 quality_score/key_dates（Phase C1 兜底）
"""
import pytest
from sqlalchemy.orm import Session

from app.models.kaoyan_news import KaoyanNews
from app.models.user import User
from app.services.news_enhance import (
    _parse_llm_json,
    _sanitize_llm_dates,
    enhance_news_item,
    schedule_news_enhancement,
)


class _FakeOrchestrator:
    """可控的 AIOrchestrator 替身：可配置返回文本或抛异常。"""

    def __init__(self, response: str | None = None, error: Exception | None = None):
        self._response = response
        self._error = error
        self.calls = 0

    async def chat(self, system_prompt: str, user_prompt: str, timeout: int = 30, **kw):
        self.calls += 1
        if self._error is not None:
            raise self._error
        return self._response


def _make_news(db: Session, **overrides) -> KaoyanNews:
    defaults = {
        "title": "2026 考研复试线公布",
        "summary": "各院校陆续公布复试分数线",
        "content": "复试时间为2025年3月25日，请考生关注院校官网。",
        "source_platform": "rss",
        "source_url": "https://news.example.com/2026/08/12",
        "status": "approved",
        "category": "复试",
        "quality_score": 60,
        "quality_grade": "B",
        "key_dates": [{"label": "复试", "date": "2026-03-25"}],
        "is_expired": False,
    }
    defaults.update(overrides)
    news = KaoyanNews(**defaults)
    db.add(news)
    db.commit()
    db.refresh(news)
    return news


class TestParseLlmJson:
    def test_plain_json(self):
        assert _parse_llm_json('{"summary": "好"}') == {"summary": "好"}

    def test_markdown_fence(self):
        raw = '```json\n{"summary": "好"}\n```'
        assert _parse_llm_json(raw) == {"summary": "好"}

    def test_prefix_and_suffix_noise(self):
        raw = '好的，以下是结果：{"summary": "好"} 以上。'
        assert _parse_llm_json(raw) == {"summary": "好"}

    def test_invalid_json_returns_none(self):
        assert _parse_llm_json("这不是 JSON") is None
        assert _parse_llm_json("") is None
        assert _parse_llm_json(None) is None


class TestSanitizeLlmDates:
    def test_keeps_valid_entries(self):
        raw = [
            {"label": "报名", "date": "2025-10-15", "end_date": "2025-10-28"},
            {"label": "初试", "date": "2025-12-20"},
        ]
        result = _sanitize_llm_dates(raw)
        assert result == [
            {"label": "报名", "date": "2025-10-15", "end_date": "2025-10-28"},
            {"label": "初试", "date": "2025-12-20"},
        ]

    def test_drops_invalid_entries(self):
        raw = [
            {"label": "报名", "date": "2025-13-45"},          # 非法日期
            {"label": "未知标签", "date": "2025-10-01"},      # 非白名单标签
            {"label": "报名", "date": "2025年10月"},           # 格式不符
            {"label": "报名", "date": None},
            "not-a-dict",
        ]
        assert _sanitize_llm_dates(raw) == []

    def test_end_date_before_date_dropped(self):
        # end_date < date：保留单点日期，丢弃非法 end_date
        result = _sanitize_llm_dates([
            {"label": "调剂", "date": "2025-04-08", "end_date": "2025-04-01"},
        ])
        assert result == [{"label": "调剂", "date": "2025-04-08"}]


class TestEnhanceNewsItem:
    @pytest.mark.asyncio
    async def test_success_backfills_fields(self, db_session, monkeypatch):
        news = _make_news(db_session)
        fake = _FakeOrchestrator(
            response=(
                '{"summary": "多校公布复试线，考生需核对报考专业线并准备复试材料。",'
                '"category": "复试线",'
                '"key_dates": [{"label": "复试", "date": "2026-03-25"}]}'
            )
        )
        monkeypatch.setattr(
            "app.services.ai_orchestrator.AIOrchestrator", lambda: fake
        )

        result = await enhance_news_item(db_session, news)
        assert result["status"] == "enhanced"
        db_session.commit()
        db_session.refresh(news)
        assert news.ai_summary and "复试线" in news.ai_summary
        assert news.category == "复试线"
        assert news.key_dates == [{"label": "复试", "date": "2026-03-25"}]

    @pytest.mark.asyncio
    async def test_llm_error_degrades_keeps_rule_based(self, db_session, monkeypatch):
        news = _make_news(db_session)
        fake = _FakeOrchestrator(error=RuntimeError("LLM 超时"))
        monkeypatch.setattr(
            "app.services.ai_orchestrator.AIOrchestrator", lambda: fake
        )

        result = await enhance_news_item(db_session, news)
        assert result["status"] == "degraded"
        db_session.refresh(news)
        # 诚实降级：ai_summary 不动，规则版 key_dates 保留
        assert news.ai_summary is None
        assert news.key_dates == [{"label": "复试", "date": "2026-03-25"}]

    @pytest.mark.asyncio
    async def test_non_json_response_degrades(self, db_session, monkeypatch):
        news = _make_news(db_session)
        fake = _FakeOrchestrator(response="抱歉，我无法完成。")
        monkeypatch.setattr(
            "app.services.ai_orchestrator.AIOrchestrator", lambda: fake
        )

        result = await enhance_news_item(db_session, news)
        assert result["status"] == "degraded"


class TestScheduleEnhancement:
    def test_memory_broker_skips(self, db_session, monkeypatch):
        """开发环境（REDIS_URL 为空 / memory broker）不投递、不阻塞。"""
        monkeypatch.setattr(
            "app.config.settings",
            type("S", (), {"REDIS_URL": None})(),
        )
        assert schedule_news_enhancement(limit=3) is False


@pytest.fixture
def admin_headers(client, db_session):
    from app.core.security import hash_password

    admin = User(
        email="admin-news@test.com",
        password_hash=hash_password("Admin1234!"),
        name="管理员",
        is_admin=True,
    )
    db_session.add(admin)
    db_session.commit()
    resp = client.post(
        "/api/auth/login",
        json={"email": "admin-news@test.com", "password": "Admin1234!"},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestPromoteFillsPurityFields:
    """Phase C1 端到端：审核 approve → 落库即带 quality/key_dates/is_expired。"""

    def test_approve_kaoyan_news_carries_purity_fields(self, client, admin_headers, db_session):
        from hashlib import sha256

        from app.models.ingestion import ExternalResearchItem, ReviewQueueItem

        source_url = "https://news.example.com/2026/08/14/pure"
        meta = {
            "summary": "2026 考研报名公告",
            "category": "政策",
            "tags": ["考研"],
            "crawled_at": "2026-08-14T08:00:00Z",
            # 模拟采集期未注入质量分（走 promote 现场计算兜底路径）
        }
        ext = ExternalResearchItem(
            crawler_name="eol_kaoyan",
            crawler_run_id="00000000000000000000000000000000",
            item_type="kaoyan_news",
            title="2026 年硕士研究生招生考试报名公告",
            content="网上报名时间为2025年10月15日至10月28日，初试时间为2025年12月20日。",
            source_url=source_url,
            source_platform="eol",
            external_meta=meta,
        )
        db_session.add(ext)
        db_session.flush()
        queue = ReviewQueueItem(
            item_type="external_research",
            ref_item_id=ext.id,
            source_url=source_url,
            review_status="PENDING",
            biz_req_no=sha256(source_url.encode("utf-8")).hexdigest()[:12],
        )
        db_session.add(queue)
        db_session.commit()

        resp = client.post(
            f"/api/admin/research-queue/{queue.id}/approve",
            json={},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["promoted"] == 1

        news = db_session.query(KaoyanNews).filter(
            KaoyanNews.source_url == source_url
        ).first()
        assert news is not None
        assert isinstance(news.quality_score, int) and 0 <= news.quality_score <= 100
        assert news.quality_grade in {"A", "B", "C", "D"}
        # 规则版关键时间点落库（报名窗口区间 + 初试单点）
        assert {"label": "报名", "date": "2025-10-15", "end_date": "2025-10-28"} in news.key_dates
        assert {"label": "初试", "date": "2025-12-20"} in news.key_dates
        assert isinstance(news.is_expired, bool)
