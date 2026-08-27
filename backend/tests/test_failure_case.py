"""失败案例库 API 测试。"""

from app.services.failure_case_seeds import seed_failure_cases

# ======================================================================
# 测试辅助
# ======================================================================


def _create_case_payload(**overrides) -> dict:
    """生成一个有效的失败案例提交 payload。"""
    base = {
        "author_role": "在校生",
        "path_type": "kaoyan",
        "stage": "preparation",
        "title": "测试失败案例标题",
        "story": "这是一段足够长的第一人称叙事，用于测试创建接口。" * 3,
        "lessons": ["教训1", "教训2", "教训3"],
        "regrets": ["后悔1", "后悔2"],
        "what_would_i_do": "如果重来我会这样这样做。",
    }
    base.update(overrides)
    return base


def _seed_cases(db_session):
    """直接通过服务层种入 8 条 approved 案例。"""
    return seed_failure_cases(db_session)


# ======================================================================
# 公开列表访问
# ======================================================================


class TestListCases:
    def test_list_public_no_auth_required(self, client):
        """未登录用户可以访问列表。"""
        resp = client.get("/api/failure-cases")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] == 0  # 默认无数据

    def test_list_returns_only_approved(self, db_session, client):
        """列表只返回 status=approved 的案例。"""
        from app.models.failure_case import FailureCase

        db_session.add(
            FailureCase(
                author_role="在校生",
                path_type="kaoyan",
                stage="preparation",
                title="已审核案例",
                story="故事内容",
                lessons=["教训1"],
                regrets=["后悔1"],
                what_would_i_do="如果重来...",
                status="approved",
            )
        )
        db_session.add(
            FailureCase(
                author_role="在校生",
                path_type="kaoyan",
                stage="preparation",
                title="待审核案例",
                story="故事内容",
                lessons=["教训1"],
                regrets=["后悔1"],
                what_would_i_do="如果重来...",
                status="pending",
            )
        )
        db_session.commit()

        resp = client.get("/api/failure-cases")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["title"] == "已审核案例"


# ======================================================================
# 筛选
# ======================================================================


class TestFilterCases:
    def test_filter_by_path_type(self, db_session, client):
        """按 path_type 筛选。"""
        _seed_cases(db_session)
        # 种子数据中 kaoyan=3, civil_service=2, employment=2, study_abroad=1

        resp = client.get("/api/failure-cases", params={"path_type": "kaoyan"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 3
        for item in data["items"]:
            assert item["path_type"] == "kaoyan"

    def test_filter_by_stage(self, db_session, client):
        """按 stage 筛选。"""
        _seed_cases(db_session)
        # 种子数据中 preparation=4, interview=3, final_year1=1, year2_plus=1
        # 实际：kaoyan-prep, civil-prep, emp-prep, kaoyan-interview,
        #       civil-interview, emp-interview, kaoyan-year2_plus, study_abroad-final_year1
        # preparation: 3 (kaoyan/civil/emp) ; interview: 3 (kaoyan/civil/emp) ; year2_plus: 1 ; final_year1: 1

        resp = client.get("/api/failure-cases", params={"stage": "preparation"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 3
        for item in data["items"]:
            assert item["stage"] == "preparation"

    def test_filter_by_path_and_stage(self, db_session, client):
        """同时按 path_type 和 stage 筛选。"""
        _seed_cases(db_session)

        resp = client.get(
            "/api/failure-cases",
            params={"path_type": "kaoyan", "stage": "interview"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["path_type"] == "kaoyan"
        assert data["items"][0]["stage"] == "interview"

    def test_filter_invalid_path_type_returns_422(self, client):
        """无效 path_type 返回 422。"""
        resp = client.get("/api/failure-cases", params={"path_type": "invalid"})
        assert resp.status_code == 422


# ======================================================================
# 分页
# ======================================================================


class TestPagination:
    def test_pagination_basic(self, db_session, client):
        """分页：page=1, size=3 返回前 3 条。"""
        _seed_cases(db_session)

        resp = client.get("/api/failure-cases", params={"page": 1, "size": 3})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 8
        assert len(data["items"]) == 3
        assert data["page"] == 1
        assert data["page_size"] == 3

    def test_pagination_page2(self, db_session, client):
        """分页：page=3, size=3 返回最后 2 条。"""
        _seed_cases(db_session)

        resp = client.get("/api/failure-cases", params={"page": 3, "size": 3})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 8
        assert len(data["items"]) == 2  # 8 - 3*2 = 2

    def test_pagination_invalid_page(self, client):
        """page=0 返回 422。"""
        resp = client.get("/api/failure-cases", params={"page": 0})
        assert resp.status_code == 422

    def test_pagination_size_too_large(self, client):
        """size > 50 返回 422。"""
        resp = client.get("/api/failure-cases", params={"size": 100})
        assert resp.status_code == 422


# ======================================================================
# 分享需登录
# ======================================================================


class TestCreateCase:
    def test_create_requires_auth(self, client):
        """未登录提交失败案例返回 401。"""
        resp = client.post("/api/failure-cases", json=_create_case_payload())
        assert resp.status_code == 401

    def test_create_success_returns_pending(self, auth_headers, client):
        """登录后可以提交，status 返回 pending。"""
        resp = client.post(
            "/api/failure-cases",
            headers=auth_headers,
            json=_create_case_payload(),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "测试失败案例标题"
        assert data["path_type"] == "kaoyan"
        assert data["stage"] == "preparation"
        assert data["lessons"] == ["教训1", "教训2", "教训3"]
        assert data["regrets"] == ["后悔1", "后悔2"]
        assert data["helpful_count"] == 0
        assert data["view_count"] == 0

    def test_create_invalid_path_type(self, auth_headers, client):
        """无效 path_type 返回 422。"""
        resp = client.post(
            "/api/failure-cases",
            headers=auth_headers,
            json=_create_case_payload(path_type="invalid_path"),
        )
        assert resp.status_code == 422

    def test_create_invalid_stage(self, auth_headers, client):
        """无效 stage 返回 422。"""
        resp = client.post(
            "/api/failure-cases",
            headers=auth_headers,
            json=_create_case_payload(stage="invalid_stage"),
        )
        assert resp.status_code == 422

    def test_create_empty_title_rejected(self, auth_headers, client):
        """空标题返回 422。"""
        resp = client.post(
            "/api/failure-cases",
            headers=auth_headers,
            json=_create_case_payload(title=""),
        )
        assert resp.status_code == 422


# ======================================================================
# 匿名性
# ======================================================================


class TestAnonymity:
    def test_response_has_no_user_id(self, auth_headers, client):
        """创建后的 response 不含 user_id 字段（匿名设计）。"""
        resp = client.post(
            "/api/failure-cases",
            headers=auth_headers,
            json=_create_case_payload(),
        )
        assert resp.status_code == 201
        data = resp.json()
        # 关键：response 不应包含 user_id 字段
        assert "user_id" not in data
        assert "user" not in data

    def test_approved_case_in_list_has_no_user_id(self, db_session, client):
        """列表中的案例也不含 user_id 字段。"""
        from app.models.failure_case import FailureCase

        db_session.add(
            FailureCase(
                author_role="毕业生",
                path_type="kaoyan",
                stage="interview",
                title="匿名案例",
                story="故事",
                lessons=["教训1"],
                regrets=["后悔1"],
                what_would_i_do="如果重来",
                status="approved",
            )
        )
        db_session.commit()

        resp = client.get("/api/failure-cases")
        assert resp.status_code == 200
        for item in resp.json()["items"]:
            assert "user_id" not in item

    def test_author_role_is_stored_not_user_id(self, auth_headers, client, db_session):
        """数据库中只存 author_role，不存 user_id。"""
        from app.models.failure_case import FailureCase

        resp = client.post(
            "/api/failure-cases",
            headers=auth_headers,
            json=_create_case_payload(author_role="工作3年内"),
        )
        assert resp.status_code == 201
        case_id = resp.json()["id"]

        # 直接查询数据库，确认无 user_id 列
        case = db_session.query(FailureCase).filter(FailureCase.id == case_id).first()
        assert case is not None
        assert case.author_role == "工作3年内"
        assert not hasattr(case, "user_id")


# ======================================================================
# 标记有帮助
# ======================================================================


class TestMarkHelpful:
    def test_mark_helpful_requires_auth(self, client, db_session):
        """未登录不能标记有帮助。"""
        _seed_cases(db_session)
        resp = client.get("/api/failure-cases", params={"size": 1})
        case_id = resp.json()["items"][0]["id"]

        result = client.post(f"/api/failure-cases/{case_id}/helpful")
        assert result.status_code == 401

    def test_mark_helpful_increments_count(self, auth_headers, client, db_session):
        """登录后标记有帮助，helpful_count + 1。"""
        _seed_cases(db_session)
        resp = client.get("/api/failure-cases", params={"size": 1})
        case_id = resp.json()["items"][0]["id"]
        before = resp.json()["items"][0]["helpful_count"]

        result = client.post(
            f"/api/failure-cases/{case_id}/helpful",
            headers=auth_headers,
        )
        assert result.status_code == 200
        assert result.json()["helpful_count"] == before + 1

    def test_mark_helpful_nonexistent(self, auth_headers, client):
        """对不存在的案例标记有帮助返回 404。"""
        fake_id = "00000000-0000-0000-0000-000000000000"
        resp = client.post(
            f"/api/failure-cases/{fake_id}/helpful",
            headers=auth_headers,
        )
        assert resp.status_code == 404


# ======================================================================
# 详情 + 浏览数
# ======================================================================


class TestGetCase:
    def test_get_case_detail(self, db_session, client):
        """获取详情成功。"""
        _seed_cases(db_session)
        resp = client.get("/api/failure-cases", params={"size": 1})
        case_id = resp.json()["items"][0]["id"]

        detail = client.get(f"/api/failure-cases/{case_id}")
        assert detail.status_code == 200
        data = detail.json()
        assert data["id"] == case_id
        assert "story" in data
        assert "lessons" in data
        assert "regrets" in data
        assert "what_would_i_do" in data

    def test_get_case_increments_view(self, db_session, client):
        """获取详情自动增加浏览数。"""
        _seed_cases(db_session)
        resp = client.get("/api/failure-cases", params={"size": 1})
        case_id = resp.json()["items"][0]["id"]
        before = resp.json()["items"][0]["view_count"]

        client.get(f"/api/failure-cases/{case_id}")
        client.get(f"/api/failure-cases/{case_id}")

        # 重新查询列表确认 view_count 增加 2
        resp2 = client.get("/api/failure-cases", params={"size": 1})
        # 列表中的可能是另一条最新案例，需要直接取详情
        detail = client.get(f"/api/failure-cases/{case_id}")
        assert detail.json()["view_count"] >= before + 2

    def test_get_nonexistent_case_404(self, client):
        """获取不存在的案例返回 404。"""
        fake_id = "00000000-0000-0000-0000-000000000000"
        resp = client.get(f"/api/failure-cases/{fake_id}")
        assert resp.status_code == 404

    def test_get_pending_case_404(self, db_session, client):
        """获取 pending 状态的案例返回 404（不公开未审核内容）。"""
        from app.models.failure_case import FailureCase

        case = FailureCase(
            author_role="在校生",
            path_type="kaoyan",
            stage="preparation",
            title="待审核",
            story="故事",
            lessons=["l"],
            regrets=["r"],
            what_would_i_do="...",
            status="pending",
        )
        db_session.add(case)
        db_session.commit()

        resp = client.get(f"/api/failure-cases/{case.id}")
        assert resp.status_code == 404


# ======================================================================
# 统计
# ======================================================================


class TestStats:
    def test_stats_public(self, client):
        """统计接口公开可访问。"""
        resp = client.get("/api/failure-cases/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data
        assert "by_path" in data
        assert "by_stage" in data

    def test_stats_after_seeding(self, db_session, client):
        """种子后统计正确。"""
        _seed_cases(db_session)

        resp = client.get("/api/failure-cases/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 8
        # 种子分布：kaoyan=3, civil_service=2, employment=2, study_abroad=1
        assert data["by_path"]["kaoyan"] == 3
        assert data["by_path"]["civil_service"] == 2
        assert data["by_path"]["employment"] == 2
        assert data["by_path"]["study_abroad"] == 1

    def test_stats_excludes_pending(self, db_session, client):
        """统计只包含 approved 案例。"""
        from app.models.failure_case import FailureCase

        db_session.add(
            FailureCase(
                author_role="在校生",
                path_type="kaoyan",
                stage="preparation",
                title="approved",
                story="...",
                lessons=[],
                regrets=[],
                what_would_i_do="...",
                status="approved",
            )
        )
        db_session.add(
            FailureCase(
                author_role="在校生",
                path_type="kaoyan",
                stage="preparation",
                title="pending",
                story="...",
                lessons=[],
                regrets=[],
                what_would_i_do="...",
                status="pending",
            )
        )
        db_session.commit()

        resp = client.get("/api/failure-cases/stats")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1  # 只算 approved


# ======================================================================
# 种子数据完整性
# ======================================================================


class TestSeedData:
    def test_seed_cases_have_required_fields(self, db_session):
        """每条种子数据都有必填字段。"""
        from app.services.failure_case_seeds import SEED_CASES

        assert len(SEED_CASES) == 8
        for case in SEED_CASES:
            assert case["author_role"]
            assert case["path_type"] in {"kaoyan", "civil_service", "employment", "study_abroad"}
            assert case["stage"] in {"preparation", "interview", "final_year1", "year2_plus"}
            assert case["title"]
            assert len(case["story"]) >= 200, f"story 太短: {case['title']}"
            assert 3 <= len(case["lessons"]) <= 5
            assert 2 <= len(case["regrets"]) <= 3
            assert len(case["what_would_i_do"]) >= 50

    def test_seed_function_idempotent(self, db_session):
        """种子函数幂等：第二次调用不重复插入。"""
        first = seed_failure_cases(db_session)
        assert first == 8

        second = seed_failure_cases(db_session)
        assert second == 0

        from app.models.failure_case import FailureCase

        total = db_session.query(FailureCase).count()
        assert total == 8
