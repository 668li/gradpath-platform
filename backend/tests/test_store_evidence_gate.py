"""地基⑤三态闸测试（spec 002 FR4，验收判据 4：无证据必拒）。

入库唯一咽喉 store_research_items 的构造性防线：
- fetched 缺证据（http_status/fetched_at/sha256 任一缺失）→ 拒收不入库；
- fetched 证据齐全 → 落库且 data_origin/fetch_evidence 列可见；
- legacy 态新写入 → 拒收（存量冻结语义，预置/合成数据从此进不来）；
- 未知 data_origin → 拒收；
- curated 无证据 → 放行（人工策展语义，无需 HTTP 证据）。
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.ingestion import ExternalResearchItem
from app.services.research_ingestion import store_research_items

_RUN_ID = "00000000000000000000000000000000"

_FULL_EVIDENCE = {
    "http_status": 200,
    "fetched_at": "2026-09-12T12:00:00+00:00",
    "sha256": "a" * 64,
    "url": "https://kaoyan.eol.cn/e_ky/zt/common/fsx/",
}


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    engine.dispose()


def _item(**overrides) -> dict:
    base = {
        "title": "2026 国家线公布",
        "content": "教育部公布 2026 年全国硕士研究生招生考试国家分数线。",
        "source_url": "https://kaoyan.eol.cn/e_ky/zt/common/fsx/index.shtml",
        "fetch_evidence": dict(_FULL_EVIDENCE),
    }
    base.update(overrides)
    return base


def _stored_origins(db) -> list:
    return [row.data_origin for row in db.query(ExternalResearchItem).all()]


def test_fetched_with_full_evidence_inserted(db):
    result = store_research_items(
        db,
        crawler_name="eol_kaoyan",
        item_type="kaoyan_news",
        items=[_item()],
        source_platform="eol",
        run_id=_RUN_ID,
    )
    assert result["inserted"] == 1
    assert result["evidence_rejected"] == 0
    row = db.query(ExternalResearchItem).one()
    assert row.data_origin == "fetched"
    assert row.fetch_evidence["sha256"] == _FULL_EVIDENCE["sha256"]
    assert row.fetch_evidence["http_status"] == 200


@pytest.mark.parametrize(
    "broken",
    [
        {"http_status": 200, "fetched_at": "2026-09-12T12:00:00+00:00"},  # 缺 sha256
        {"http_status": 200, "sha256": "a" * 64},  # 缺 fetched_at
        {"fetched_at": "2026-09-12T12:00:00+00:00", "sha256": "a" * 64},  # 缺 http_status
        {"http_status": 500, "fetched_at": "t", "sha256": "a" * 64},  # 非成功状态
        {"http_status": 200, "fetched_at": "", "sha256": "a" * 64},  # 空时刻
        "not-a-dict",  # 证据不是结构化对象
    ],
)
def test_fetched_without_evidence_rejected(db, broken):
    result = store_research_items(
        db,
        crawler_name="eol_kaoyan",
        item_type="kaoyan_news",
        items=[_item(fetch_evidence=broken)],
        source_platform="eol",
        run_id=_RUN_ID,
    )
    assert result["inserted"] == 0
    assert result["evidence_rejected"] == 1
    assert _stored_origins(db) == []


def test_fetched_missing_evidence_key_rejected(db):
    """run() 盖章缺位（如直连旁路构造的 items）→ 默认 fetched 语义下必拒。"""
    result = store_research_items(
        db,
        crawler_name="eol_kaoyan",
        item_type="kaoyan_news",
        items=[_item(fetch_evidence=None)],
        source_platform="eol",
        run_id=_RUN_ID,
    )
    assert result["inserted"] == 0
    assert result["evidence_rejected"] == 1


def test_legacy_state_rejected_for_new_writes(db):
    """预置/合成数据的出口被构造性焊死：legacy 新写入一律拒收。"""
    result = store_research_items(
        db,
        crawler_name="yanzhao",
        item_type="kaoyan_news",
        items=[_item(fetch_evidence=None)],
        source_platform="web",
        run_id=_RUN_ID,
        data_origin="legacy",
    )
    assert result["inserted"] == 0
    assert result["evidence_rejected"] == 1
    assert _stored_origins(db) == []


def test_unknown_origin_rejected(db):
    """三态之外没有第四种状态（蓝图⑤）。"""
    result = store_research_items(
        db,
        crawler_name="eol_kaoyan",
        item_type="kaoyan_news",
        items=[_item(data_origin="synthesized")],
        source_platform="eol",
        run_id=_RUN_ID,
    )
    assert result["inserted"] == 0
    assert result["evidence_rejected"] == 1


def test_curated_allowed_without_evidence(db):
    """curated=人工策展语义：无需 HTTP 证据，照实落列。"""
    result = store_research_items(
        db,
        crawler_name="seed_from_research",
        item_type="kaoyan_news",
        items=[_item(fetch_evidence=None)],
        source_platform="web",
        run_id=_RUN_ID,
        data_origin="curated",
    )
    assert result["inserted"] == 1
    row = db.query(ExternalResearchItem).one()
    assert row.data_origin == "curated"
    assert row.fetch_evidence is None
