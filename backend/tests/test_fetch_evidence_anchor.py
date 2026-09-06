"""抓取证据锚（对抗审计 F1）+ 快速通道三条件（F5）+ 质量门槛全类型（F7）回归。

核心语义：official_verified 不再由 URL 域名自证——必须同时存在
BaseCrawler._request 产生的真实 HTTP 留痕（external_meta.fetched_evidence）。
留痕只能由 _request 写入（假管道想拿证据必须真的发 HTTP）。
"""

from app.crawlers.base_crawler import BaseCrawler
from app.models.ingestion import ExternalResearchItem, ReviewQueueItem
from app.models.user import User
from app.services.research_auto_review import auto_review_pending
from app.services.research_ingestion import _infer_credibility, store_research_items

_EDU_URL = "https://lab.univ-test.edu.cn/notice/1"


def _make_probe() -> BaseCrawler:
    class _Probe(BaseCrawler):
        name = "evidence_probe"
        category = "test"

        def fetch(self):
            return []

        def parse(self, raw):
            return raw

        def store(self, items, db=None):
            return 0

    return _Probe()


def _wire_fake_http(monkeypatch, crawler):
    """只替身网络 IO；_request 主体（校验/限速/留痕）真实执行。"""

    class _Resp:
        status_code = 200
        text = "<html>ok</html>"

        def raise_for_status(self):
            return None

    class _Sess:
        def request(self, method, url, timeout=None, **kw):
            return _Resp()

    monkeypatch.setattr(crawler, "_get_session", lambda: _Sess())
    monkeypatch.setattr(crawler, "_validate_outbound_url", lambda url: (True, ""))
    monkeypatch.setattr(crawler, "_check_robots_allowed", lambda url: True)
    monkeypatch.setattr(crawler, "_throttle", lambda host: None)


# ---------------------------------------------------------------- 双条件打标


def test_official_domain_without_evidence_downgrades():
    """仅有官方域名、无抓取留痕 → model_inferred（手写 URL 不再自证官方）。"""
    assert _infer_credibility(_EDU_URL, "official", None) == "model_inferred"
    assert _infer_credibility(_EDU_URL, "official", []) == "model_inferred"
    assert _infer_credibility("https://www.gov.cn/ze/2026.htm", "web", None) == "model_inferred"


def test_request_log_enables_official_verified(monkeypatch):
    """经 _request 真实留痕的官方域名条目 → official_verified。"""
    crawler = _make_probe()
    _wire_fake_http(monkeypatch, crawler)

    crawler._request(_EDU_URL)

    evidence = crawler.fetch_evidence()
    assert len(evidence) == 1
    assert evidence[0]["status"] == 200 and evidence[0]["url"] == _EDU_URL and evidence[0]["at"]
    assert _infer_credibility(_EDU_URL, "official", evidence) == "official_verified"


def test_fetch_log_immutable_snapshot(monkeypatch):
    """fetch_evidence 返回拷贝：调用方篡改不影响内部留痕（防伪造证据）。"""
    crawler = _make_probe()
    _wire_fake_http(monkeypatch, crawler)
    crawler._request(_EDU_URL)

    snapshot = crawler.fetch_evidence()
    snapshot.clear()
    assert len(crawler.fetch_evidence()) == 1


# ---------------------------------------------------------------- store 证据落库


def test_store_persists_fetched_evidence(db_session):
    result = store_research_items(
        db_session,
        crawler_name="official_announce",
        item_type="kaoyan_news",
        items=[{"title": "官方公告", "content": "x" * 80, "source_url": _EDU_URL}],
        source_platform="official",
        run_id="0" * 32,
        fetch_log=[{"url": _EDU_URL, "status": 200, "at": "2026-09-06T08:00:00+00:00"}],
    )
    assert result["inserted"] == 1
    ext = (
        db_session.query(ExternalResearchItem)
        .filter(ExternalResearchItem.source_url == _EDU_URL)
        .one()
    )
    ev = (ext.external_meta or {}).get("fetched_evidence")
    assert ev and ev[0]["status"] == 200 and ev[0]["at"]


def test_store_without_evidence_keeps_meta_clean(db_session):
    """不传 fetch_log：不写 fetched_evidence 键（历史路径兼容）。"""
    store_research_items(
        db_session,
        crawler_name="official_announce",
        item_type="kaoyan_news",
        items=[{"title": "公告", "content": "y" * 80, "source_url": "https://other.univ.edu.cn/b"}],
        source_platform="official",
        run_id="0" * 32,
    )
    ext = (
        db_session.query(ExternalResearchItem)
        .filter(ExternalResearchItem.source_url == "https://other.univ.edu.cn/b")
        .one()
    )
    assert "fetched_evidence" not in (ext.external_meta or {})


# ---------------------------------------------------------------- F5 快速通道三条件


def _seed_admin(db_session):
    db_session.add(
        User(
            email="auto-admin@example.com",
            password_hash="x",
            name="管理员",
            is_admin=True,
        )
    )
    db_session.commit()


def _seed_pending(db_session, *, evidence: bool):
    meta = (
        {"fetched_evidence": [{"url": _EDU_URL, "status": 200, "at": "2026-09-06T08:00:00+00:00"}]}
        if evidence
        else {}
    )
    ext = ExternalResearchItem(
        crawler_name="official_announce",
        crawler_run_id="0" * 32,
        item_type="kaoyan_news",
        title="官方通知正文足够长的标题示例用于通过评分门槛2026",
        content="根据教育部有关规定，我校2027年硕士研究生招生考试实行网上报名，逾期不再补报，也不得修改报名信息。"
        * 12,
        source_url=_EDU_URL,
        source_platform="official",
        external_meta={
            **meta,
            "published_at": "2026-09-06T07:00:00+00:00",
        },
        credibility="official_verified",
        review_status="PENDING",
    )
    db_session.add(ext)
    db_session.flush()
    db_session.add(
        ReviewQueueItem(
            item_type="external_research",
            ref_item_id=ext.id,
            source_url=_EDU_URL,
            review_status="PENDING",
            biz_req_no=f"research:official_announce:{abs(hash(_EDU_URL)) % 10**12:012d}",
        )
    )
    # 快速通道门槛：少量人工历史 ≥OFFICIAL_MIN_HISTORY(5)（人工/自动标记在
    # 队列表 reviewed_by 上——F5 靠 join ReviewQueueItem 排除自动放行）
    for i in range(6):
        hist = ExternalResearchItem(
            crawler_name="official_announce",
            crawler_run_id="0" * 32,
            item_type="kaoyan_news",
            title=f"历史人工已审条目{i}",
            content="c" * 100,
            source_url=f"https://hist.univ-test.edu.cn/{i}",
            source_platform="official",
            credibility="official_verified",
            review_status="APPROVED",
        )
        db_session.add(hist)
        db_session.flush()
        db_session.add(
            ReviewQueueItem(
                item_type="external_research",
                ref_item_id=hist.id,
                source_url=hist.source_url,
                review_status="APPROVED",
                reviewed_by="human-admin@example.com",
                biz_req_no=f"research:hist:{i:012d}",
            )
        )
    db_session.commit()
    return ext


def test_fast_track_rejects_official_without_evidence(db_session):
    """官方域名但无抓取留痕 → 快速通道不可用，不自动放行（F1+F5）。"""
    _seed_admin(db_session)
    _seed_pending(db_session, evidence=False)
    stats = auto_review_pending(db_session)
    assert stats.get("gate_evidence", 0) >= 1
    assert stats.get("auto_approved", 0) == 0


# ---------------------------------------------------------------- F7 门槛全类型


def test_quality_gate_applies_to_all_item_types(db_session):
    """quality_score 低于阈值的 experience_post 同样不占审核队列（F7）。"""
    result = store_research_items(
        db_session,
        crawler_name="bilibili_research",
        item_type="experience_post",
        items=[
            {
                "title": "低质经验帖",
                "content": "z" * 80,
                "source_url": "https://www.bilibili.com/video/BV1xx",
                "quality_score": 20,
            }
        ],
        source_platform="bilibili",
        run_id="0" * 32,
    )
    assert result["inserted"] == 0


def test_items_without_quality_score_unaffected(db_session):
    """未携带 quality_score 的条目照常入库（isinstance 防线保留）。"""
    result = store_research_items(
        db_session,
        crawler_name="bilibili_research",
        item_type="experience_post",
        items=[
            {
                "title": "无评分经验帖",
                "content": "q" * 80,
                "source_url": "https://www.bilibili.com/video/BV1yy",
            }
        ],
        source_platform="bilibili",
        run_id="0" * 32,
    )
    assert result["inserted"] == 1
