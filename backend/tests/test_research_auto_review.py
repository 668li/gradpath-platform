"""三闸门自动放行（research_auto_review）单元测试。

覆盖：来源信誉闸门（低通过率被挡）、质量分闸门（低分保持 PENDING）、
研招网红线防御驳回、全过闸门自动放行并 promote 落业务表。
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models.ingestion import ExternalResearchItem, ReviewQueueItem
from app.models.user import User
from app.services.research_auto_review import auto_review_pending, source_reputation

GOOD_CRAWLER = "rsshub_research"
BAD_CRAWLER = "web_article_research"


def _mk_admin(db):
    admin = User(
        email="sysadmin@test.com",
        password_hash="x" * 64,
        name="sysadmin",
        is_admin=True,
    )
    db.add(admin)
    db.commit()
    return admin


def _mk_history(db, crawler: str, approved: int, rejected: int) -> None:
    """制造历史审核画像（直接落已审核条目，不进队列）。"""
    for i in range(approved):
        db.add(
            ExternalResearchItem(
                crawler_name=crawler,
                crawler_run_id="seed",
                item_type="kaoyan_news",
                title=f"{crawler} 历史通过 {i}",
                content="历史种子内容" * 20,
                source_url=f"https://seed.example.com/{crawler}/a/{i}",
                source_platform="rsshub",
                review_status="APPROVED",
            )
        )
    for i in range(rejected):
        db.add(
            ExternalResearchItem(
                crawler_name=crawler,
                crawler_run_id="seed",
                item_type="kaoyan_news",
                title=f"{crawler} 历史驳回 {i}",
                content="历史种子内容" * 20,
                source_url=f"https://seed.example.com/{crawler}/r/{i}",
                source_platform="rsshub",
                review_status="REJECTED",
            )
        )
    db.commit()


def _mk_pending(db, crawler: str, title: str, url: str, content: str = "") -> ExternalResearchItem:
    ext = ExternalResearchItem(
        crawler_name=crawler,
        crawler_run_id="run-1",
        item_type="kaoyan_news",
        title=title,
        content=content or (title + "。") * 40,
        source_url=url,
        source_platform="rsshub",
        review_status="PENDING",
    )
    db.add(ext)
    db.flush()
    db.add(
        ReviewQueueItem(
            item_type="external_research",
            ref_item_id=ext.id,
            source_url=url,
            review_status="PENDING",
            biz_req_no=url,
        )
    )
    db.commit()
    return ext


@pytest.fixture
def seeded(db_session):
    _mk_admin(db_session)
    # 好源：30 过 0 驳（pass_rate=1.0, total=30 达标）
    _mk_history(db_session, GOOD_CRAWLER, approved=30, rejected=0)
    # 坏源：30 过 10 驳（pass_rate=0.75 低于 0.9）
    _mk_history(db_session, BAD_CRAWLER, approved=30, rejected=10)
    return db_session


def test_source_reputation_calculated(seeded):
    rep = source_reputation(seeded)
    assert rep[GOOD_CRAWLER]["pass_rate"] == 1.0
    assert rep[GOOD_CRAWLER]["total"] == 30
    assert rep[BAD_CRAWLER]["pass_rate"] == 0.75


def test_high_quality_from_trusted_source_auto_approved(seeded):
    ext = _mk_pending(
        seeded,
        GOOD_CRAWLER,
        "华中农业大学研究生院发布2026年硕士研究生招生复试分数线公告",
        "https://yjs.hzau.edu.cn/info/1/2026.htm",
    )
    stats = auto_review_pending(seeded)
    assert stats["auto_approved"] == 1
    seeded.refresh(ext)
    assert ext.review_status == "APPROVED"
    assert stats["promoted"] == 1


def test_low_reputation_source_blocked(seeded):
    _mk_pending(
        seeded,
        BAD_CRAWLER,
        "某考研机构发布的经验分享文章标题",
        "https://blog.example.com/post/1",
    )
    stats = auto_review_pending(seeded)
    assert stats["gate_reputation"] == 1
    assert stats["auto_approved"] == 0


def test_low_score_blocked(seeded):
    _mk_pending(
        seeded,
        GOOD_CRAWLER,
        "通知",
        "https://yjs.hzau.edu.cn/info/2/2026.htm",
        content="短内容",
    )
    stats = auto_review_pending(seeded)
    assert stats["gate_score"] == 1
    assert stats["auto_approved"] == 0


def test_chsi_redline_defensively_rejected(seeded):
    ext = _mk_pending(
        seeded,
        GOOD_CRAWLER,
        "研招网调剂信息",
        "https://yz.chsi.com.cn/kyzx/tjxx/2026/1.htm",
    )
    stats = auto_review_pending(seeded)
    assert stats["chsi_rejected"] == 1
    seeded.refresh(ext)
    assert ext.review_status == "REJECTED"


def test_official_fast_track_bypasses_history_threshold(db_session):
    """官方源快速通道：零驳回 + official_verified + 历史≥5 即放行（不足 30）。"""
    _mk_admin(db_session)
    official = "official_announce"
    # 历史 6 条全过（<30，走普通信誉闸会被挡）
    for i in range(6):
        db_session.add(
            ExternalResearchItem(
                crawler_name=official,
                crawler_run_id="seed",
                item_type="kaoyan_news",
                title=f"官方公告历史 {i}",
                content="官方历史内容" * 30,
                source_url=f"https://yjs.hzau.edu.cn/info/1/{i}.htm",
                source_platform="official",
                credibility="official_verified",
                review_status="APPROVED",
            )
        )
    db_session.commit()
    ext = _mk_pending(
        db_session,
        official,
        "华中农业大学2026年硕士研究生招生复试资格线公告",
        "https://yjs.hzau.edu.cn/info/2/2026.htm",
    )
    ext.credibility = "official_verified"
    db_session.commit()
    stats = auto_review_pending(db_session)
    assert stats["auto_approved"] == 1
    db_session.refresh(ext)
    assert ext.review_status == "APPROVED"


def test_official_with_rejection_history_needs_full_threshold(db_session):
    """官方源一旦有驳回历史，必须走普通信誉闸（≥30 条）。"""
    _mk_admin(db_session)
    official = "official_announce"
    for i in range(6):
        db_session.add(
            ExternalResearchItem(
                crawler_name=official,
                crawler_run_id="seed",
                item_type="kaoyan_news",
                title=f"官方公告历史 {i}",
                content="官方历史内容" * 30,
                source_url=f"https://yjs.hzau.edu.cn/info/1/{i}.htm",
                source_platform="official",
                credibility="official_verified",
                review_status="APPROVED",
            )
        )
    db_session.add(
        ExternalResearchItem(
            crawler_name=official,
            crawler_run_id="seed",
            item_type="kaoyan_news",
            title="被驳回的官方条目",
            content="内容" * 50,
            source_url="https://yjs.hzau.edu.cn/info/1/bad.htm",
            source_platform="official",
            credibility="official_verified",
            review_status="REJECTED",
        )
    )
    db_session.commit()
    _mk_pending(
        db_session,
        official,
        "华中农业大学2026年硕士研究生招生复试资格线公告",
        "https://yjs.hzau.edu.cn/info/2/2026.htm",
    )
    stats = auto_review_pending(db_session)
    assert stats["gate_reputation"] == 1
    assert stats["auto_approved"] == 0


def test_dry_run_makes_no_changes(seeded):
    _mk_pending(
        seeded,
        GOOD_CRAWLER,
        "华中农业大学研究生院发布2026年硕士研究生招生复试分数线公告",
        "https://yjs.hzau.edu.cn/info/3/2026.htm",
    )
    stats = auto_review_pending(seeded, dry_run=True)
    assert stats["auto_approved"] == 1
    pending = (
        seeded.query(ReviewQueueItem).filter(ReviewQueueItem.review_status == "PENDING").count()
    )
    assert pending >= 1  # dry-run 未改动


# --- explain / limit：只读观测能力（2026-10-01 CLI 入口配套）---


def _mk_long_title(tag: str) -> str:
    """造一个正文足够长（≥1000 字）能过质量分闸的标题。"""
    return f"{tag} " + "研究生招生公告正文内容" * 60


def test_explain_details_align_with_counters(seeded):
    """逐条明细与四类计数必须闭合：每条 PENDING 恰好落一个 verdict。"""
    _mk_pending(
        seeded, GOOD_CRAWLER, _mk_long_title("官方复试线"), "https://yjs.hzau.edu.cn/info/9/a.htm"
    )
    _mk_pending(
        seeded, GOOD_CRAWLER, "通知", "https://yjs.hzau.edu.cn/info/9/b.htm", content="短内容"
    )
    _mk_pending(seeded, BAD_CRAWLER, "某考研机构经验分享", "https://blog.example.com/post/9")
    _mk_pending(
        seeded, GOOD_CRAWLER, "研招网调剂信息", "https://yz.chsi.com.cn/kyzx/tjxx/2026/9.htm"
    )

    stats = auto_review_pending(seeded, dry_run=True, explain=True)
    details = stats["details"]

    assert len(details) == stats["pending"] == 4
    counted = (
        stats["auto_approved"]
        + stats["gate_reputation"]
        + stats["gate_score"]
        + stats["chsi_rejected"]
    )
    assert counted == len(details) == 4
    assert {d["verdict"] for d in details} == {
        "pass_standard",
        "block_score",
        "block_reputation",
        "reject_redline",
    }
    assert all(d["reason"] for d in details)
    assert any(d["host"] == "yjs.hzau.edu.cn" for d in details)
    blocked = next(d for d in details if d["verdict"] == "block_score")
    assert blocked["score"] is not None and "门槛" in blocked["reason"]


def test_explain_off_by_default_keeps_legacy_shape(seeded):
    """默认 explain=False：既有调用方（爬虫任务）拿到的 dict 不带明细。"""
    _mk_pending(
        seeded, GOOD_CRAWLER, _mk_long_title("官方公告"), "https://yjs.hzau.edu.cn/info/11/a.htm"
    )
    stats = auto_review_pending(seeded, dry_run=True)
    assert stats["details"] == []
    assert stats["auto_approved"] == 1


def test_limit_caps_processing(seeded):
    """--limit 灰度：只处理队列最靠前的 N 条，其余保持 PENDING。"""
    for i in range(3):
        _mk_pending(
            seeded,
            GOOD_CRAWLER,
            _mk_long_title(f"官方公告{i}"),
            f"https://yjs.hzau.edu.cn/info/2{i}/2026.htm",
        )
    stats = auto_review_pending(seeded, dry_run=True, explain=True, limit=2)
    assert stats["pending"] == 2
    assert stats["auto_approved"] == 2
    assert len(stats["details"]) == 2


def test_dry_run_order_is_deterministic(seeded):
    """同一批 PENDING 两次 dry-run 必须给出同一顺序（逐条 diff 的前提）。"""
    for i in range(3):
        _mk_pending(
            seeded,
            GOOD_CRAWLER,
            _mk_long_title(f"排序用例{i}"),
            f"https://yjs.hzau.edu.cn/info/3{i}/2026.htm",
        )
    first = [
        d["ref_item_id"] for d in auto_review_pending(seeded, dry_run=True, explain=True)["details"]
    ]
    second = [
        d["ref_item_id"] for d in auto_review_pending(seeded, dry_run=True, explain=True)["details"]
    ]
    assert first == second == sorted(first)
