"""grad_intel.py API 端点测试。

覆盖：
- 院校情报 CRUD（保存、列表、删除）
- AI 院校情报查询（mock LLM）
- 自我定位（创建、最新、历史、清除缓存）
- 暗知识（列表、阶段、预填充）
- 公开浏览接口（院校情报、研招网数据、分数线、调剂、院校汇总）
- 导师评价（列表、详情、评价列表）
"""
import time
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.cache import cache
from app.models.grad_intel import (
    DarkKnowledge,
    GradAdjustmentInfo,
    GradSchoolIntel,
    GradScorelineRecord,
    GradYanzhaoProgram,
    SelfPositioning,
)
from app.models.mentor import Mentor
from app.models.mentor_review import MentorReview
from app.services import grad_intel_service


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
        resp = client.delete(
            f"/api/grad-intel/intel/{intel_id}", headers=auth_headers
        )
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_delete_intel_not_found(self, client: TestClient, auth_headers):
        fake_id = str(uuid4())
        resp = client.delete(
            f"/api/grad-intel/intel/{fake_id}", headers=auth_headers
        )
        assert resp.status_code == 404


# ======================================================================
# AI 院校情报查询
# ======================================================================
class TestIntelQuery:
    def test_query_intel_with_mock_llm(self, client: TestClient, auth_headers):
        mock_result = {
            "school_name": "清华大学",
            "major_name": "计算机科学与技术",
            "school_tier": "985",
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
            "insider_notes": "保护一志愿",
            "data_sources": ["研招网"],
            "tags": ["985"],
            "ai_summary": "顶级院校",
        }
        # 修复: grad_intel_service 使用 AIOrchestrator 而非 AIService
        with patch(
            "app.services.grad_intel_service.AIOrchestrator"
        ) as MockOrch:
            mock_orch = MagicMock()
            mock_orch.chat = AsyncMock(return_value=__import__("json").dumps(mock_result))
            MockOrch.return_value = mock_orch

            resp = client.post(
                "/api/grad-intel/intel/query",
                json={"school_name": "清华大学", "major_name": "计算机科学与技术"},
                headers=auth_headers,
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["school_name"] == "清华大学"

    def test_query_intel_llm_failure_returns_503(self, client: TestClient, auth_headers):
        with patch(
            "app.services.grad_intel_service.AIOrchestrator"
        ) as MockOrch:
            mock_orch = MagicMock()
            mock_orch.chat = AsyncMock(side_effect=Exception("LLM 连接失败"))
            MockOrch.return_value = mock_orch

            resp = client.post(
                "/api/grad-intel/intel/query",
                json={"school_name": "test", "major_name": "test"},
                headers=auth_headers,
            )
        assert resp.status_code == 503

    def test_query_intel_requires_auth(self, client: TestClient):
        resp = client.post(
            "/api/grad-intel/intel/query",
            json={"school_name": "test", "major_name": "test"},
        )
        assert resp.status_code == 401


# ======================================================================
# 自我定位
# ======================================================================
class TestPositioning:
    def _create_positioning(self, client, auth_headers, **overrides):
        body = {
            "undergrad_tier": "985",
            "undergrad_major": "计算机科学与技术",
            "gpa": 3.6,
            "gpa_rank": "前20%",
            "english_level": "CET-6",
            "english_score": 520,
            "research_experience": "发表1篇SCI",
            "competitions": ["ACM银牌"],
            "target_major": "计算机科学与技术",
            "target_region": "北京",
        }
        body.update(overrides)
        return client.post(
            "/api/grad-intel/positioning/create",
            json=body,
            headers=auth_headers,
        )

    def test_create_positioning(self, client: TestClient, auth_headers):
        resp = self._create_positioning(client, auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["undergrad_tier"] == "985"
        assert data["gpa"] == 3.6
        assert "reach_schools" in data
        assert "target_schools" in data
        assert "safety_schools" in data
        assert "success_probability" in data

    def test_create_positioning_with_bypass_cache(self, client: TestClient, auth_headers):
        resp1 = self._create_positioning(client, auth_headers, bypass_cache="true")
        assert resp1.status_code == 200
        resp2 = self._create_positioning(client, auth_headers, bypass_cache="true")
        assert resp2.status_code == 200

    def test_get_latest_positioning(self, client: TestClient, auth_headers):
        self._create_positioning(client, auth_headers)
        resp = client.get(
            "/api/grad-intel/positioning/latest", headers=auth_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data is not None
        assert data["undergrad_tier"] == "985"

    def test_get_latest_positioning_empty(self, client: TestClient, auth_headers):
        resp = client.get(
            "/api/grad-intel/positioning/latest", headers=auth_headers
        )
        assert resp.status_code == 200
        assert resp.json() is None

    def test_get_positioning_history(self, client: TestClient, auth_headers):
        self._create_positioning(client, auth_headers)
        resp = client.get(
            "/api/grad-intel/positioning/history", headers=auth_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_clear_positioning_cache(self, client: TestClient, auth_headers):
        resp = client.post(
            "/api/grad-intel/positioning/clear-cache", headers=auth_headers
        )
        assert resp.status_code == 200
        assert "缓存已清除" in resp.json()["message"]

    def test_positioning_requires_auth(self, client: TestClient):
        resp = client.post(
            "/api/grad-intel/positioning/create",
            json={"undergrad_tier": "985"},
        )
        assert resp.status_code == 401


# ======================================================================
# 暗知识
# ======================================================================
class TestDarkKnowledge:
    def _seed_dark_knowledge(self, client, auth_headers=None):
        """辅助：通过 API 触发暗知识预填充。"""
        headers = auth_headers or {}
        resp = client.post("/api/grad-intel/dark-knowledge/seed", headers=headers)
        assert resp.status_code == 200, f"seed 失败: {resp.text}"
        return resp.json()

    def test_list_dark_knowledge(self, client: TestClient, auth_headers):
        """list 接口返回分页结构 {items, total, page, limit, pages}。"""
        # 先 seed 数据（list 接口公开，但 seed 需要登录）
        self._seed_dark_knowledge(client, auth_headers)
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

    def test_list_dark_knowledge_by_stage(self, client: TestClient, auth_headers):
        self._seed_dark_knowledge(client, auth_headers)
        cache.clear()

        resp = client.get(
            "/api/grad-intel/dark-knowledge/list", params={"stage": "decision"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)
        assert "items" in data
        assert all(item["stage"] == "decision" for item in data["items"])

    def test_dark_knowledge_stages(self, client: TestClient, auth_headers):
        self._seed_dark_knowledge(client, auth_headers)
        cache.clear()

        resp = client.get("/api/grad-intel/dark-knowledge/stages")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert "stage" in data[0]
        assert "name" in data[0]
        assert "count" in data[0]

    def test_seed_dark_knowledge(self, client: TestClient, auth_headers):
        resp = client.post(
            "/api/grad-intel/dark-knowledge/seed", headers=auth_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "seeded" in data
        assert "total" in data

    def test_seed_dark_knowledge_idempotent(self, client: TestClient, auth_headers):
        resp1 = client.post(
            "/api/grad-intel/dark-knowledge/seed", headers=auth_headers
        )
        resp2 = client.post(
            "/api/grad-intel/dark-knowledge/seed", headers=auth_headers
        )
        assert resp1.status_code == 200
        assert resp2.status_code == 200
        assert resp1.json()["seeded"] > 0
        assert resp2.json()["seeded"] == 0

    def test_seed_requires_auth(self, client: TestClient):
        resp = client.post("/api/grad-intel/dark-knowledge/seed")
        assert resp.status_code == 401


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
        resp = client.get(
            "/api/grad-intel/intel/public", params={"school_name": "北京"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert all("北京" in i["school_name"] for i in data)

    def test_list_public_intel_filter_tier(self, client: TestClient, db_session, auth_headers):
        from app.models.user import User

        user = db_session.query(User).first()
        self._seed_intel(db_session, user.id)
        cache.clear()
        resp = client.get(
            "/api/grad-intel/intel/public", params={"school_tier": "985"}
        )
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


class TestScorelines:
    def _seed_scoreline(self, db_session):
        record = GradScorelineRecord(
            university_name="北京大学",
            major_name="软件工程",
            degree_type="学术学位",
            year=2025,
            total_score_line=350,
            politics_score=55,
            foreign_language_score=55,
            business_1_score=90,
            business_2_score=90,
            enrollment_count=15,
            application_count=200,
        )
        db_session.add(record)
        db_session.commit()
        return record

    def test_list_scorelines(self, client: TestClient, db_session):
        self._seed_scoreline(db_session)
        cache.clear()
        resp = client.get("/api/grad-intel/scorelines")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]["total_score_line"] == 350

    def test_list_scorelines_filter(self, client: TestClient, db_session):
        self._seed_scoreline(db_session)
        cache.clear()
        resp = client.get(
            "/api/grad-intel/scorelines",
            params={"university_name": "北京", "year": 2025},
        )
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_scoreline_trend(self, client: TestClient, db_session):
        for year in [2023, 2024, 2025]:
            record = GradScorelineRecord(
                university_name="复旦大学",
                major_name="计算机科学",
                degree_type="学术学位",
                year=year,
                total_score_line=340 + (year - 2023) * 5,
            )
            db_session.add(record)
        db_session.commit()
        cache.clear()
        resp = client.get(
            "/api/grad-intel/scorelines/trend",
            params={
                "university_name": "复旦大学",
                "major_name": "计算机科学",
                "degree_type": "学术学位",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["university_name"] == "复旦大学"
        assert len(data["years"]) == 3
        assert data["years"] == [2023, 2024, 2025]

    def test_scoreline_trend_empty(self, client: TestClient):
        cache.clear()
        resp = client.get(
            "/api/grad-intel/scorelines/trend",
            params={"university_name": "不存在的大学", "major_name": "不存在的专业"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["years"] == []


class TestAdjustments:
    def _seed_adjustment(self, db_session):
        adj = GradAdjustmentInfo(
            university_name="浙江大学",
            department="信息与电子工程学院",
            major_name="电子科学与技术",
            degree_type="学术学位",
            adjustment_quota=5,
            contact_email="yzb@zju.edu.cn",
            deadline="2025-04-10",
            year=2025,
            status="open",
        )
        db_session.add(adj)
        db_session.commit()
        return adj

    def test_list_adjustments(self, client: TestClient, db_session):
        self._seed_adjustment(db_session)
        cache.clear()
        resp = client.get("/api/grad-intel/adjustments")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_list_adjustments_filter(self, client: TestClient, db_session):
        self._seed_adjustment(db_session)
        cache.clear()
        resp = client.get(
            "/api/grad-intel/adjustments",
            params={"university_name": "浙江大学", "status": "open"},
        )
        assert resp.status_code == 200
        assert len(resp.json()) >= 1


class TestSchoolSummary:
    def _seed_school_data(self, db_session):
        prog = GradYanzhaoProgram(
            university_name="中国科学技术大学",
            department="计算机科学与技术学院",
            major_name="计算机科学与技术",
            degree_type="学术学位",
            year=2026,
        )
        record = GradScorelineRecord(
            university_name="中国科学技术大学",
            major_name="计算机科学与技术",
            degree_type="学术学位",
            year=2025,
            total_score_line=345,
        )
        adj = GradAdjustmentInfo(
            university_name="中国科学技术大学",
            department="计算机学院",
            major_name="计算机科学与技术",
            year=2025,
            status="open",
        )
        db_session.add_all([prog, record, adj])
        db_session.commit()

    def test_school_summary(self, client: TestClient, db_session):
        self._seed_school_data(db_session)
        cache.clear()
        resp = client.get(
            "/api/grad-intel/schools/中国科学技术大学/summary"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["university_name"] == "中国科学技术大学"
        assert data["program_count"] >= 1
        assert data["latest_scoreline"] == 345
        assert data["has_adjustment"] is True
        assert data["adjustment_count"] >= 1

    def test_school_summary_empty(self, client: TestClient):
        cache.clear()
        resp = client.get(
            "/api/grad-intel/schools/不存在的大学/summary"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["program_count"] == 0
        assert data["has_adjustment"] is False


# ======================================================================
# 导师评价
# ======================================================================
class TestMentors:
    def _seed_mentor(self, db_session):
        mentor = Mentor(
            name="张教授",
            university="北京大学",
            department="计算机科学技术学院",
            title="教授",
            research_directions=["机器学习", "自然语言处理"],
            paper_count=50,
            project_count=10,
            citation_count=2000,
            h_index=30,
            enrollment_status="accepting",
            avg_rating=4.5,
            review_count=12,
        )
        db_session.add(mentor)
        db_session.commit()
        return mentor

    def _seed_review(self, db_session, mentor_id, user_id):
        review = MentorReview(
            mentor_id=mentor_id,
            user_id=user_id,
            is_anonymous=True,
            anonymous_id="2023级硕士",
            rating_academic=5,
            rating_guidance=4,
            rating_relationship=4,
            rating_funding=3,
            rating_workload=3,
            rating_career=5,
            overall_rating=4.0,
            title="学术能力强",
            content="张教授学术水平很高，论文产出稳定。",
            review_status="approved",
            submitted_at="2025-01-01T00:00:00",
        )
        db_session.add(review)
        db_session.commit()
        return review

    def test_list_mentors(self, client: TestClient, db_session):
        self._seed_mentor(db_session)
        resp = client.get("/api/grad-intel/mentors")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] >= 1

    def test_list_mentors_filter_university(self, client: TestClient, db_session):
        self._seed_mentor(db_session)
        resp = client.get(
            "/api/grad-intel/mentors",
            params={"university": "北京"},
        )
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    def test_list_mentors_filter_rating(self, client: TestClient, db_session):
        self._seed_mentor(db_session)
        resp = client.get(
            "/api/grad-intel/mentors",
            params={"min_rating": 4.0},
        )
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    def test_mentor_detail(self, client: TestClient, db_session):
        mentor = self._seed_mentor(db_session)
        resp = client.get(f"/api/grad-intel/mentors/{mentor.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "张教授"
        assert data["university"] == "北京大学"

    def test_mentor_detail_not_found(self, client: TestClient):
        fake_id = str(uuid4())
        resp = client.get(f"/api/grad-intel/mentors/{fake_id}")
        assert resp.status_code == 404

    def test_mentor_reviews(self, client: TestClient, db_session, auth_headers):
        from app.models.user import User

        user = db_session.query(User).filter(User.email == "test@example.com").first()
        mentor = self._seed_mentor(db_session)
        self._seed_review(db_session, mentor.id, user.id)
        resp = client.get(f"/api/grad-intel/mentors/{mentor.id}/reviews")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert data["total"] >= 1

    def test_mentor_reviews_not_found(self, client: TestClient):
        fake_id = str(uuid4())
        resp = client.get(f"/api/grad-intel/mentors/{fake_id}/reviews")
        assert resp.status_code == 404


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

    def test_positioning_minimal_fields(self, client: TestClient, auth_headers):
        resp = client.post(
            "/api/grad-intel/positioning/create",
            json={"undergrad_tier": "二本"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["undergrad_tier"] == "二本"
        assert "reach_schools" in data

    def test_dark_knowledge_no_auth_required(self, client: TestClient):
        resp = client.get("/api/grad-intel/dark-knowledge/list")
        assert resp.status_code == 200

    def test_public_intel_no_auth_required(self, client: TestClient):
        resp = client.get("/api/grad-intel/intel/public")
        assert resp.status_code == 200

    def test_yanzhao_programs_no_auth_required(self, client: TestClient):
        resp = client.get("/api/grad-intel/yanzhao-programs")
        assert resp.status_code == 200

    def test_scorelines_no_auth_required(self, client: TestClient):
        resp = client.get("/api/grad-intel/scorelines")
        assert resp.status_code == 200

    def test_adjustments_no_auth_required(self, client: TestClient):
        resp = client.get("/api/grad-intel/adjustments")
        assert resp.status_code == 200

    def test_mentors_no_auth_required(self, client: TestClient):
        resp = client.get("/api/grad-intel/mentors")
        assert resp.status_code == 200

    def test_scoreline_trend_no_auth_required(self, client: TestClient):
        resp = client.get(
            "/api/grad-intel/scorelines/trend",
            params={"university_name": "test", "major_name": "test"},
        )
        assert resp.status_code == 200

    def test_school_summary_no_auth_required(self, client: TestClient):
        resp = client.get("/api/grad-intel/schools/test/summary")
        assert resp.status_code == 200
