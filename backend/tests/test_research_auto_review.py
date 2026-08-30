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


def test_dry_run_makes_no_changes(seeded):
    _mk_pending(
        seeded,
        GOOD_CRAWLER,
        "华中农业大学研究生院发布2026年硕士研究生招生复试分数线公告",
        "https://yjs.hzau.edu.cn/info/3/2026.htm",
    )
    stats = auto_review_pending(seeded, dry_run=True)
    assert stats["auto_approved"] == 1
    pending = seeded.query(ReviewQueueItem).filter(ReviewQueueItem.review_status == "PENDING").count()
    assert pending >= 1  # dry-run 未改动
