# tests/test_resource_links.py
"""资源导航测试 — RN-1d（2026-10-03 任务书：资源导航聚合中心）。

锁定契约：
- seed 质量：≥25 条候选 / 每条带实测记录 / 0 条 forbidden / 全部 pending 待终审；
- API 行为：pending 外显带徽章字段 / killed·retired·forbidden 不外显 / 过滤器；
- 点名制红线：user_approved 默认 false，seed 不含任何自动转正路径。
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import pytest
from fastapi.testclient import TestClient

from app.models.resource_link import (
    RESOURCE_CATEGORY_KAOYAN,
    RESOURCE_COPYRIGHT_CAUTION,
    RESOURCE_COPYRIGHT_FORBIDDEN,
    RESOURCE_COPYRIGHT_ORIGINAL,
    RESOURCE_STATUS_ACTIVE,
    RESOURCE_STATUS_KILLED,
    RESOURCE_STATUS_PENDING,
    ResourceLink,
)
from app.services.resource_link_seed import _LINKS, seed_resource_links


@pytest.fixture()
def seeded_db(db_session):
    seed_resource_links(db_session)
    return db_session


# ======================================================================
# RN-1d seed 质量门（任务书验收：候选池 ≥25 全带实测记录，0 forbidden）
# ======================================================================


class TestSeedQualityGate:
    def test_at_least_25_candidates(self):
        assert len(_LINKS) >= 25, f"候选数 {len(_LINKS)} < 25，RN-4 验收不达标"

    def test_every_candidate_has_probe_record(self):
        for spec in _LINKS:
            assert spec["sources"], f"{spec['name']} 无实测记录（禁止预填凑数）"
            for src in spec["sources"]:
                # 实测记录必须含核验时间与判定（HTTP 200 或仓库活跃度二选一）
                assert "checked_at" in src and "verdict" in src, f"{spec['name']} 源记录不完整"
                assert ("http_status" in src) or ("stars" in src), f"{spec['name']} 源缺实测数值"

    def test_zero_forbidden(self):
        for spec in _LINKS:
            assert spec.get("copyright_tier") != RESOURCE_COPYRIGHT_FORBIDDEN, (
                f"{spec['name']} 版权档为 forbidden，永不入库"
            )

    def test_caution_tier_has_risk_note(self):
        for spec in _LINKS:
            if spec.get("copyright_tier") == RESOURCE_COPYRIGHT_CAUTION:
                assert spec.get("risk_note"), f"{spec['name']} 灰区档必须带风险注记"

    def test_every_candidate_has_note(self):
        for spec in _LINKS:
            assert spec.get("note"), f"{spec['name']} 缺一句话定位（note 必填）"


class TestSeedIdempotent:
    def test_seed_twice_insert_once(self, db_session):
        first = seed_resource_links(db_session)
        second = seed_resource_links(db_session)
        assert first[0] >= 25 and first[1] == 0
        assert second == (0, first[0])
        assert db_session.query(ResourceLink).count() == first[0]

    def test_all_pending_and_unapproved(self, seeded_db):
        links = seeded_db.query(ResourceLink).all()
        assert links
        for l in links:
            assert l.status == RESOURCE_STATUS_PENDING, f"{l.name} 必须 pending（点名制）"
            assert l.user_approved is False, f"{l.name} user_approved 必须 false（终审唯一闸）"


# ======================================================================
# RN-1b API 行为
# ======================================================================


class TestResourceApi:
    def test_list_returns_pending_with_badge(self, seeded_db, client):
        resp = client.get("/api/resources")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 25
        assert data["pending_count"] == data["total"], "初始池应全部 pending"
        for item in data["items"]:
            assert item["pending_review"] is True
            assert item["user_approved"] is False
            assert item["note"], "每卡必须带一句话定位"

    def test_category_filter(self, seeded_db, client):
        resp = client.get("/api/resources", params={"category": RESOURCE_CATEGORY_KAOYAN})
        assert resp.status_code == 200
        for item in resp.json()["items"]:
            assert item["category"] == RESOURCE_CATEGORY_KAOYAN

    def test_query_filter(self, seeded_db, client):
        resp = client.get("/api/resources", params={"q": "408"})
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    def test_killed_and_forbidden_never_visible(self, seeded_db, client):
        killed = ResourceLink(
            name="被杀条目",
            url="https://example.com/killed",
            track="kaoyan",
            category=RESOURCE_CATEGORY_KAOYAN,
            note="测试用",
            status=RESOURCE_STATUS_KILLED,
            sources=[{"checked_at": "2026-10-03", "verdict": "ok"}],
        )
        forbidden = ResourceLink(
            name="盗版条目",
            url="https://example.com/forbidden",
            track="kaoyan",
            category=RESOURCE_CATEGORY_KAOYAN,
            note="测试用",
            copyright_tier=RESOURCE_COPYRIGHT_FORBIDDEN,
            sources=[{"checked_at": "2026-10-03", "verdict": "ok"}],
        )
        seeded_db.add_all([killed, forbidden])
        seeded_db.commit()

        resp = client.get("/api/resources")
        urls = [i["url"] for i in resp.json()["items"]]
        assert "https://example.com/killed" not in urls
        assert "https://example.com/forbidden" not in urls

    def test_active_sorts_before_pending(self, seeded_db, client):
        approved = ResourceLink(
            name="已转正条目",
            url="https://example.com/active",
            track="kaoyan",
            category=RESOURCE_CATEGORY_KAOYAN,
            note="测试用",
            status=RESOURCE_STATUS_ACTIVE,
            user_approved=True,
            sources=[{"checked_at": "2026-10-03", "verdict": "ok"}],
        )
        seeded_db.add(approved)
        seeded_db.commit()

        data = client.get("/api/resources").json()
        assert data["items"][0]["url"] == "https://example.com/active"
        assert data["items"][0]["pending_review"] is False
        assert data["active_count"] == 1
