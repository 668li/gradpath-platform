"""grad_intel.py API 端点测试。

覆盖：
- 院校情报 CRUD（保存、列表、删除）
- 暗知识（列表、阶段；预填充端点已随功能下架删除）
- 公开浏览接口（院校情报、研招网数据、院校公告归口）
"""

from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.cache import cache
from app.models.grad_intel import DarkKnowledge, GradSchoolIntel, GradYanzhaoProgram


# ======================================================================
# 院校情报 CRUD
# ======================================================================
class TestIntelCRUD:
    def test_save_intel(self, client: TestClient, auth_headers):
        resp = client.post(
            "/api/grad-intel/intel/save",
            json={
                "school_name": "清华大学",
                "major_name": "计算机科学与技术",
                "school_tier": "985",
                "year": 2026,
                "background_discrimination": "light",
                "first_choice_protection": "yes",
                "admission_ratio": "15:1",
                "push_ratio": "60%",
                "actual_quota": 20,
                "score_line": 360,
                "retest_weight": "50%",
                "retest_format": "笔试+面试",
                "score_suppression": "none",
                "transfer_friendly": "yes",
                "insider_notes": "保护第一志愿",
                "data_sources": ["研招网"],
                "tags": ["985", "计算机"],
                "ai_summary": "顶级院校",
                "is_ai_generated": True,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["school_name"] == "清华大学"
        assert data["major_name"] == "计算机科学与技术"
        assert data["school_tier"] == "985"
        assert data["admission_ratio"] == "15:1"
        assert data["push_ratio"] == "60%"
        assert data["actual_quota"] == 20
        assert data["is_ai_generated"] is True
        assert "id" in data

    def test_save_intel_requires_auth(self, client: TestClient):
        resp = client.post(
            "/api/grad-intel/intel/save",
            json={"school_name": "test", "major_name": "test"},
        )
        assert resp.status_code == 401

    def test_list_intel(self, client: TestClient, auth_headers):
        client.post(
            "/api/grad-intel/intel/save",
            json={"school_name": "浙江大学", "major_name": "软件工程"},
            headers=auth_headers,
        )
        resp = client.get("/api/grad-intel/intel/list", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(i["school_name"] == "浙江大学" for i in data)

    def test_list_intel_empty(self, client: TestClient, auth_headers):
        resp = client.get("/api/grad-intel/intel/list", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_delete_intel(self, client: TestClient, auth_headers):
        save_resp = client.post(
            "/api/grad-intel/intel/save",
            json={"school_name": "南京大学", "major_name": "物理学"},
            headers=auth_headers,
        )
        intel_id = save_resp.json()["id"]
        resp = client.delete(f"/api/grad-intel/intel/{intel_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_delete_intel_not_found(self, client: TestClient, auth_headers):
        fake_id = str(uuid4())
        resp = client.delete(f"/api/grad-intel/intel/{fake_id}", headers=auth_headers)
        assert resp.status_code == 404


# ======================================================================
# 暗知识
# ======================================================================
class TestDarkKnowledge:
    def _seed_dark_knowledge(self, db_session):
        """辅助：直接入库造数（原 seed 端点已随暗知识下架删除）。"""
        row = DarkKnowledge(
            stage="decision",
            category="ROI评估",
            title="测试条目",
            content="测试内容",
            importance="high",
            sort_order=1,
        )
        db_session.add(row)
        db_session.commit()
        return row

    def test_list_dark_knowledge(self, client: TestClient, db_session):
        """list 接口返回分页结构 {items, total, page, limit, pages}。"""
        self._seed_dark_knowledge(db_session)
        cache.clear()

        resp = client.get("/api/grad-intel/dark-knowledge/list")
        assert resp.status_code == 200
        data = resp.json()
        # 修复: 接口返回分页 dict 而非 list
        assert isinstance(data, dict)
        assert "items" in data
        assert "total" in data
        assert data["total"] > 0
        assert len(data["items"]) > 0
        first = data["items"][0]
        assert "title" in first
        assert "stage" in first
        assert "content" in first

    def test_list_dark_knowledge_by_stage(self, client: TestClient, db_session):
        self._seed_dark_knowledge(db_session)
        cache.clear()

        resp = client.get("/api/grad-intel/dark-knowledge/list", params={"stage": "decision"})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)
        assert "items" in data
        assert all(item["stage"] == "decision" for item in data["items"])

    def test_dark_knowledge_stages(self, client: TestClient, db_session):
        self._seed_dark_knowledge(db_session)
        cache.clear()

        resp = client.get("/api/grad-intel/dark-knowledge/stages")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert "stage" in data[0]
        assert "name" in data[0]
        assert "count" in data[0]


# ======================================================================
# 公开浏览接口 — 院校情报
# ======================================================================
class TestPublicIntel:
    def _seed_intel(self, db_session, user_id):
        intel = GradSchoolIntel(
            user_id=user_id,
            school_name="北京大学",
            major_name="软件工程",
            school_tier="985",
            year=2026,
            background_discrimination="light",
            first_choice_protection="yes",
            data_sources=["公开资料"],
            tags=["985"],
        )
        db_session.add(intel)
        db_session.commit()
        return intel

    def test_list_public_intel(self, client: TestClient, db_session, auth_headers):
        from app.models.user import User

        user = db_session.query(User).first()
        self._seed_intel(db_session, user.id)
        cache.clear()
        resp = client.get("/api/grad-intel/intel/public")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_list_public_intel_filter_school(self, client: TestClient, db_session, auth_headers):
        from app.models.user import User

        user = db_session.query(User).first()
        self._seed_intel(db_session, user.id)
        cache.clear()
        resp = client.get("/api/grad-intel/intel/public", params={"school_name": "北京"})
        assert resp.status_code == 200
        data = resp.json()
        assert all("北京" in i["school_name"] for i in data)

    def test_list_public_intel_filter_tier(self, client: TestClient, db_session, auth_headers):
        from app.models.user import User

        user = db_session.query(User).first()
        self._seed_intel(db_session, user.id)
        cache.clear()
        resp = client.get("/api/grad-intel/intel/public", params={"school_tier": "985"})
        assert resp.status_code == 200
        data = resp.json()
        assert all(i["school_tier"] == "985" for i in data)


# ======================================================================
# 公开浏览接口 — 研招网数据
# ======================================================================
class TestYanzhaoPrograms:
    def _seed_program(self, db_session):
        prog = GradYanzhaoProgram(
            university_name="清华大学",
            department="计算机科学与技术系",
            major_name="计算机科学与技术",
            degree_type="学术学位",
            research_directions=["机器学习", "系统结构"],
            enrollment_quota=30,
            tuition="8000/年",
            duration="3年",
            study_mode="全日制",
            year=2026,
        )
        db_session.add(prog)
        db_session.commit()
        return prog

    def test_list_programs(self, client: TestClient, db_session):
        self._seed_program(db_session)
        cache.clear()
        resp = client.get("/api/grad-intel/yanzhao-programs")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_list_programs_filter_university(self, client: TestClient, db_session):
        self._seed_program(db_session)
        cache.clear()
        resp = client.get(
            "/api/grad-intel/yanzhao-programs",
            params={"university_name": "清华"},
        )
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_list_programs_filter_year(self, client: TestClient, db_session):
        self._seed_program(db_session)
        cache.clear()
        resp = client.get(
            "/api/grad-intel/yanzhao-programs",
            params={"year": 2026},
        )
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_programs_cache_hit(self, client: TestClient, db_session):
        self._seed_program(db_session)
        cache.clear()
        resp1 = client.get("/api/grad-intel/yanzhao-programs")
        resp2 = client.get("/api/grad-intel/yanzhao-programs")
        assert resp1.status_code == 200
        assert resp2.status_code == 200


# ======================================================================
# 边界情况与错误处理
# ======================================================================
class TestEdgeCases:
    def test_intel_save_minimal_fields(self, client: TestClient, auth_headers):
        resp = client.post(
            "/api/grad-intel/intel/save",
            json={"school_name": "最小字段测试", "major_name": "测试专业"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["school_tier"] == ""
        assert data["background_discrimination"] == "unknown"

    def test_dark_knowledge_no_auth_required(self, client: TestClient):
        resp = client.get("/api/grad-intel/dark-knowledge/list")
        assert resp.status_code == 200

    def test_public_intel_no_auth_required(self, client: TestClient):
        resp = client.get("/api/grad-intel/intel/public")
        assert resp.status_code == 200

    def test_yanzhao_programs_no_auth_required(self, client: TestClient):
        resp = client.get("/api/grad-intel/yanzhao-programs")
        assert resp.status_code == 200


# ======================================================================
# 院校官方公告归口
# ======================================================================
class TestSchoolAnnouncements:
    """验证归口规则：域名后缀匹配 + 校区歧义解歧 + skip 域名过滤。"""

    def _seed_approved_news(self, db_session, url: str, category: str, title: str):
        from app.models.kaoyan_news import KaoyanNews

        news = KaoyanNews(
            title=title,
            summary="测试摘要",
            source_url=url,
            source_platform="rss",
            status="approved",
            category=category,
            tags=["测试"],
        )
        db_session.add(news)
        db_session.commit()
        return news

    def test_cup_east_campus_attributed(self, client: TestClient, db_session):
        """zs.gs.upc.edu.cn（华东校区）应归口到中国石油大学（华东）。"""
        self._seed_approved_news(
            db_session,
            "http://zs.gs.upc.edu.cn/2026/0612/c10708a494873/page.htm",
            "研招公告·中国石油大学研究生院",
            "中国石油大学（华东）2026年硕士研究生招生考试初试成绩复核结果",
        )
        cache.clear()
        resp = client.get("/api/grad-intel/schools/中国石油大学（华东）/announcements")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert "复核结果" in data[0]["title"]

    def test_cup_east_not_attributed_to_beijing(self, client: TestClient, db_session):
        """华东公告不应归口到中国石油大学（北京）。"""
        self._seed_approved_news(
            db_session,
            "http://zs.gs.upc.edu.cn/2026/0612/c10708a494873/page.htm",
            "研招公告·中国石油大学研究生院",
            "中国石油大学（华东）2026年硕士研究生招生考试初试成绩复核结果",
        )
        cache.clear()
        resp = client.get("/api/grad-intel/schools/中国石油大学（北京）/announcements")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_skip_domain_still_filtered(self, client: TestClient, db_session):
        """教育部 / 公众号域名仍不归口到任何院校。"""
        self._seed_approved_news(
            db_session,
            "http://www.moe.gov.cn/2026/some-policy.htm",
            "研招公告·政策解读",
            "教育部政策公告",
        )
        self._seed_approved_news(
            db_session,
            "https://mp.weixin.qq.com/s/abc123",
            "研招公告·某校研究生院",
            "公众号文章",
        )
        cache.clear()
        for school in ("清华大学", "北京大学", "中国石油大学（华东）"):
            resp = client.get(f"/api/grad-intel/schools/{school}/announcements")
            assert resp.status_code == 200
            assert resp.json() == []

    def test_pending_news_not_attributed(self, client: TestClient, db_session):
        """未审核（pending）公告不归口。"""
        from app.models.kaoyan_news import KaoyanNews

        news = KaoyanNews(
            title="待审核公告",
            summary=None,
            source_url="http://zs.gs.upc.edu.cn/2026/9999/c99999a999999/page.htm",
            source_platform="rss",
            status="pending",
            category="研招公告·中国石油大学研究生院",
            tags=["测试"],
        )
        db_session.add(news)
        db_session.commit()
        cache.clear()
        resp = client.get("/api/grad-intel/schools/中国石油大学（华东）/announcements")
        assert resp.status_code == 200
        assert resp.json() == []


# ======================================================================
# 负例：定位链旧端点已随拍板①删除（009 T1 对账——404 为准）
# ======================================================================
class TestPositioningEndpointsRemoved:
    def test_positioning_endpoints_gone(self, client: TestClient, auth_headers):
        """定位链页面/API 已删（009 拍板①）：旧端点必须 404，不得复活。"""
        for path in (
            "/api/grad-intel/positioning/latest",
            "/api/grad-intel/positioning/history",
        ):
            resp = client.get(path, headers=auth_headers)
            assert resp.status_code == 404, f"{path} 应已 404，实际 {resp.status_code}"

        resp = client.post("/api/grad-intel/positioning/create", json={}, headers=auth_headers)
        assert resp.status_code == 404, "positioning/create 应已 404"
