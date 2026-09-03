# backend/tests/test_review_risk.py
"""M2 审核队列风险排序 + S3 主题信号 — 红/黄/绿分档让高危条目置顶。

覆盖：
- compute_review_risk 三档：离题强锚点→high / 无领域信号→medium / 正常领域帖→low
- 软广信号：强营销词→high；质量分过低→high
- API 集成：PENDING 列表 risk 字段存在且高危排前；已审列表不算风险
"""

import pytest
from sqlalchemy.orm import Session

from app.models.ingestion import ExternalResearchItem
from app.services.review_risk import compute_review_risk


def _make_ext(
    *,
    title: str,
    content: str = "",
    item_type: str = "experience_post",
    source_platform: str = "bilibili",
    source_url: str = "https://example.com/x",
    credibility: str = "model_inferred",
    external_meta: dict | None = None,
) -> ExternalResearchItem:
    return ExternalResearchItem(
        crawler_name="bilibili_research",
        crawler_run_id="0" * 32,
        item_type=item_type,
        title=title,
        content=content,
        source_url=source_url,
        source_platform=source_platform,
        external_meta=external_meta or {},
        credibility=credibility,
        review_status="PENDING",
    )


class TestComputeReviewRisk:
    def test_off_topic_anchor_is_high(self):
        """S3 核心：离题强锚点（游戏）→ high，理由含主题离题。"""
        ext = _make_ext(
            title="三角洲行动单三心态教学",
            content="这期视频讲游戏心态",
            external_meta={"tags": ["游戏"]},
        )
        grade, score, reasons = compute_review_risk(ext)
        assert grade == "high"
        assert score >= 40
        assert any("主题离题" in r for r in reasons)

    def test_no_domain_signal_is_medium(self):
        """汤家凤式无关键词正当内容 → medium（存疑待人工，不误杀）。"""
        ext = _make_ext(title="汤家凤概率论基础班", content="跟着汤老师打好基础")
        grade, _score, reasons = compute_review_risk(ext)
        assert grade == "medium"
        assert any("无领域信号" in r for r in reasons)

    def test_normal_domain_post_is_low(self):
        ext = _make_ext(
            title="考研复试经验分享", content="复试流程与注意事项，祝大家考研上岸"
        )
        grade, score, reasons = compute_review_risk(ext)
        assert grade == "low"
        assert score == 0
        assert reasons == []

    def test_strong_promotion_is_high(self):
        ext = _make_ext(
            title="考研数学保分班",
            content="包过押题名额有限，加微信领资料",
            external_meta={"tags": ["课程"]},
        )
        grade, _score, reasons = compute_review_risk(ext)
        assert grade == "high"
        assert any("软广" in r for r in reasons)

    def test_official_verified_low_signal(self):
        """官方来源给 low 信号（不改变档位，只加分说明）。"""
        ext = _make_ext(
            title="考研复试经验分享",
            content="复试流程与注意事项，祝大家考研上岸",
            credibility="official_verified",
        )
        grade, score, reasons = compute_review_risk(ext)
        assert grade == "low"
        # low 信号累计 5 分且带官方来源理由
        assert score == 5
        assert any("官方来源" in r for r in reasons)


class TestPendingListRiskSort:
    @pytest.fixture
    def admin_headers(self, client, db_session):
        from app.core.security import hash_password
        from app.models.user import User

        admin = User(
            email="risk-admin@test.com",
            password_hash=hash_password("Admin1234!"),
            name="风险管理员",
            is_admin=True,
        )
        db_session.add(admin)
        db_session.commit()
        resp = client.post(
            "/api/auth/login",
            json={"email": "risk-admin@test.com", "password": "Admin1234!"},
        )
        return {"Authorization": f"Bearer {resp.json()['access_token']}"}

    def _seed(self, db: Session) -> None:
        from hashlib import md5

        from app.models.ingestion import ReviewQueueItem

        items = [
            _make_ext(
                title="正常考研复试经验",
                content="复试流程与注意事项，祝大家考研上岸",
                source_url="https://example.com/ok",
            ),
            _make_ext(
                title="三角洲行动皮肤展示",
                content="新皮肤效果演示",
                source_url="https://example.com/game",
            ),
        ]
        for ext in items:
            db.add(ext)
            db.flush()
            db.add(
                ReviewQueueItem(
                    item_type="external_research",
                    ref_item_id=ext.id,
                    source_url=ext.source_url,
                    review_status="PENDING",
                    biz_req_no=f"risk:{md5(ext.source_url.encode()).hexdigest()[:12]}",
                )
            )
        db.commit()

    def test_pending_has_risk_fields_and_high_first(self, client, db_session, admin_headers):
        self._seed(db_session)
        resp = client.get("/api/admin/research-queue/pending", headers=admin_headers)
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 2
        assert all(it["risk_grade"] is not None for it in items)
        assert items[0]["risk_grade"] == "high"
        assert any("主题离题" in r for r in items[0]["risk_reasons"])
        assert items[1]["risk_grade"] != "high"

    def test_non_pending_has_no_risk(self, client, db_session, admin_headers):
        from hashlib import md5

        from app.models.ingestion import ReviewQueueItem

        ext = _make_ext(title="正常考研复试经验", content="复试内容",
                        source_url="https://example.com/done")
        db_session.add(ext)
        db_session.flush()
        db_session.add(
            ReviewQueueItem(
                item_type="external_research",
                ref_item_id=ext.id,
                source_url=ext.source_url,
                review_status="APPROVED",
                biz_req_no=f"risk:{md5(ext.source_url.encode()).hexdigest()[:12]}",
            )
        )
        db_session.commit()
        resp = client.get(
            "/api/admin/research-queue/pending",
            params={"review_status": "APPROVED"},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert items and items[0]["risk_grade"] is None
