"""报考条件账本测试 — 条件清单规则生成 + 勾选状态 + 完成率。"""

from app.models.gwy_position import GwyPosition


def _make_position(**overrides) -> GwyPosition:
    base = dict(
        id="a" * 32,
        year=2026,
        exam_type="国考",
        position_code="0401267001",
        position_name="科技管理一级行政执法员",
        dept_name="杭州海关",
        major_req="计算机科学与技术、软件工程、网络工程",
        education_req="仅限本科",
        degree_req="学士",
        political_status="不限",
        min_work_years="无限制",
        grassroots_exp_req="无限制",
        professional_test="否",
        interview_ratio="3:1",
        remarks="应届高校毕业生；大学英语四级考试425分及以上；现场一线岗位",
    )
    base.update(overrides)
    return GwyPosition(**base)


def _seed(client):
    from app.main import app

    # 拿到 client 背后的 session 种入职位
    session = None
    for override in app.dependency_overrides.values():
        gen = override()
        session = next(gen)
        break
    assert session is not None, "get_db override 未注册"
    session.add(_make_position())
    session.commit()


def test_checklist_generation_rules(client, auth_headers):
    """条件清单按规则生成：证书从 remarks 提取，『不限』类不生成无效条目。"""
    _seed(client)
    resp = client.get("/api/condition-checklist/" + "a" * 32, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()

    keys = [c["key"] for c in data["conditions"]]
    assert "education" in keys and "major" in keys and "degree" in keys
    # 政治面貌=不限、基层年限=无限制 → 不生成条目
    assert "political" not in keys
    assert "work_years" not in keys
    assert "grassroots" not in keys
    # professional_test=否 → 不生成
    assert "professional_test" not in keys
    # 证书要求从 remarks 提取到英语四级
    cert_keys = [k for k in keys if k.startswith("cert_")]
    assert len(cert_keys) >= 1
    cert_item = next(c for c in data["conditions"] if c["key"] == cert_keys[0])
    assert "四级" in cert_item["required"]
    assert cert_item["source_field"] == "remarks"
    # 溯源字段
    edu_item = next(c for c in data["conditions"] if c["key"] == "education")
    assert edu_item["required"] == "仅限本科"
    assert edu_item["source_field"] == "education_req"


def test_checklist_progress_and_vacuous_automet(client, auth_headers):
    """『不限』类条件自动计为已满足；未勾选条件默认 unmet。"""
    from app.schemas.user_condition import ConditionItem
    from app.services.condition_checklist_service import compute_progress

    conditions = [
        ConditionItem(
            key="education", label="学历要求", required="仅限本科", source_field="education_req"
        ),
        ConditionItem(
            key="cert_0", label="证书要求 1", required="英语四级425分及以上", source_field="remarks"
        ),
    ]
    progress = compute_progress(conditions, {})
    assert progress.total == 2
    assert progress.unmet == 2
    assert progress.rate == 0.0

    progress = compute_progress(conditions, {"education": "met", "cert_0": "in_progress"})
    assert progress.met == 1 and progress.in_progress == 1
    assert progress.rate == 50.0

    # 『不限』条件无需勾选即自动已满足
    vacuous = [
        ConditionItem(
            key="political", label="政治面貌", required="不限", source_field="political_status"
        )
    ]
    progress = compute_progress(vacuous, {})
    assert progress.met == 1 and progress.rate == 100.0


def test_status_upsert_roundtrip(client, auth_headers):
    """勾选状态落库并在清单响应里反映完成率。"""
    _seed(client)
    pid = "a" * 32

    resp = client.put(
        "/api/condition-checklist/status",
        json={"position_id": pid, "condition_key": "education", "status": "met"},
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["statuses"]["education"] == "met"
    assert data["progress"]["met"] >= 1

    # 再勾一条 → 覆盖为 in_progress
    resp = client.put(
        "/api/condition-checklist/status",
        json={"position_id": pid, "condition_key": "education", "status": "in_progress"},
        headers=auth_headers,
    )
    assert resp.json()["statuses"]["education"] == "in_progress"

    # 完成率出现在响应中且为百分比
    assert 0 <= resp.json()["progress"]["rate"] <= 100


def test_status_rejects_invalid_key_and_value(client, auth_headers):
    """条件键必须在该职位清单中；状态必须为三态之一。"""
    _seed(client)
    pid = "a" * 32

    # 非清单内的条件键 → 400
    resp = client.put(
        "/api/condition-checklist/status",
        json={"position_id": pid, "condition_key": "not_exist", "status": "met"},
        headers=auth_headers,
    )
    assert resp.status_code == 400

    # 非法状态 → 422（schema pattern 校验）
    resp = client.put(
        "/api/condition-checklist/status",
        json={"position_id": pid, "condition_key": "major", "status": "done"},
        headers=auth_headers,
    )
    assert resp.status_code == 422


def test_checklist_404_for_unknown_position(client, auth_headers):
    resp = client.get("/api/condition-checklist/" + "f" * 32, headers=auth_headers)
    assert resp.status_code == 404


def _make_province_position(**overrides):
    from app.models.gwy_province_position import GwyProvincePosition

    base = dict(
        id="b" * 32,
        year=2026,
        province="广东",
        position_code="119000125001",
        position_name="一级警员",
        dept_name="深圳市公安局",
        education_req="本科以上",
        degree_req="学士以上",
        major_req_undergrad="法学类（A0301）、公安学类（A0306）",
        grassroots_exp_req="否",
        psych_test="是",
        fresh_grad_only="应届毕业生",
        other_requirements="中共党员",
    )
    base.update(overrides)
    return GwyProvincePosition(**base)


def _seed_row(client, row):
    from app.main import app

    session = None
    for override in app.dependency_overrides.values():
        session = next(override())
        break
    assert session is not None, "get_db override 未注册"
    session.add(row)
    session.commit()


def test_province_checklist_generation(client, auth_headers):
    """省考清单：三档专业合并、是/否型列按值生成、other_requirements 短文本成条。"""
    _seed_row(client, _make_province_position())

    resp = client.get(
        "/api/condition-checklist/" + "b" * 32 + "?source=province",
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["exam_source"] == "province"

    keys = {c["key"] for c in data["conditions"]}
    assert "education" in keys and "degree" in keys and "major" in keys
    # grassroots=否 → 不生成；psych_test=是 → 生成；应届限制 → 生成
    assert "grassroots" not in keys
    assert "psych_test" in keys
    assert "fresh_grad" in keys
    # other_requirements=中共党员 → 其他要求条目
    assert "other_req" in keys
    merged = next(c for c in data["conditions"] if c["key"] == "major")
    assert "本科：" in merged["required"]

    # 省考赛道勾选独立落库
    resp = client.put(
        "/api/condition-checklist/status",
        json={
            "position_id": "b" * 32,
            "exam_source": "province",
            "condition_key": "education",
            "status": "met",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["statuses"]["education"] == "met"

    # 国考表里没有这个 id → 404（赛道隔离）
    resp = client.get(
        "/api/condition-checklist/" + "b" * 32,
        headers=auth_headers,
    )
    assert resp.status_code == 404


def test_latest_condition_summary(client, auth_headers):
    """摘要取最近核对的目标职位：完成率与赛道正确。"""
    from app.database import get_db
    from app.main import app
    from app.services.condition_checklist_service import get_latest_condition_summary

    _seed_row(client, _make_position())  # a*32 国考

    session = next(app.dependency_overrides[get_db]())
    headers = auth_headers

    # 无勾选 → None
    resp = client.get("/api/auth/me", headers=headers)
    user_id = resp.json()["id"]
    assert get_latest_condition_summary(session, user_id) is None

    # 勾选一条 → 摘要出现，rate = 1/total
    client.put(
        "/api/condition-checklist/status",
        json={"position_id": "a" * 32, "condition_key": "education", "status": "met"},
        headers=headers,
    )
    summary = get_latest_condition_summary(session, user_id)
    assert summary is not None
    assert summary["exam_source"] == "national"
    assert summary["position_code"] == "0401267001"
    assert summary["met"] >= 1
    assert 0 < summary["rate"] <= 100


def _make_kaoyan_program(**overrides):
    from app.models.grad_intel import GradYanzhaoProgram

    base = dict(
        id="c" * 32,
        university_name="清华大学",
        department="计算机系",
        major_name="计算机科学与技术",
        degree_type="学硕",
        year=2026,
        enrollment_quota=25,
        admission_requirements="仅接收推免生以外的统考生；不接受同等学力报考",
    )
    base.update(overrides)
    return GradYanzhaoProgram(**base)


def _make_kaoyan_scoreline(**overrides):
    from app.models.grad_intel import GradScorelineRecord

    base = dict(
        id="d" * 32,
        university_name="清华大学",
        major_name="计算机科学与技术",
        degree_type="学硕",
        year=2025,
        total_score_line=380,
        politics_score=50,
        foreign_language_score=50,
        business_1_score=90,
        business_2_score=95,
    )
    base.update(overrides)
    return GradScorelineRecord(**base)


def test_kaoyan_checklist_generation(client, auth_headers):
    """考研清单：最新一年复试线总分+四门单科线+报名要求；total=0 脏数据不生成。"""
    _seed_row(client, _make_kaoyan_program())
    _seed_row(
        client,
        _make_kaoyan_scoreline(),
    )
    # 更早年份的另一条线 → 必须取 2025 最新
    _seed_row(
        client,
        _make_kaoyan_scoreline(id="e" * 32, year=2024, total_score_line=372),
    )
    # 同院校另一专业的 0 分占位脏数据 → 不得污染
    _seed_row(
        client,
        _make_kaoyan_scoreline(
            id="f" * 32,
            major_name="软件工程",
            total_score_line=0,
            politics_score=0,
        ),
    )

    resp = client.get(
        "/api/condition-checklist/" + "c" * 32 + "?source=kaoyan",
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["exam_source"] == "kaoyan"
    assert data["dept_name"] == "清华大学"
    assert "计算机科学与技术" in data["position_name"]

    by_key = {c["key"]: c for c in data["conditions"]}
    assert by_key["total_score"]["required"] == "初试 ≥380 分（2025 复试线）"
    assert by_key["politics"]["required"] == "政治 ≥50 分（2025）"
    assert by_key["business_2"]["required"] == "业务课二 ≥95 分（2025）"
    assert "admission" in by_key

    # 考研赛道勾选独立落库
    resp = client.put(
        "/api/condition-checklist/status",
        json={"position_id": "c" * 32, "exam_source": "kaoyan",
              "condition_key": "total_score", "status": "in_progress"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["statuses"]["total_score"] == "in_progress"


def test_kaoyan_checklist_without_scoreline(client, auth_headers):
    """无分数线匹配时清单只剩报名要求，不报错。"""
    _seed_row(client, _make_kaoyan_program(id="9" * 32, university_name="未知大学"))
    resp = client.get(
        "/api/condition-checklist/" + "9" * 32 + "?source=kaoyan",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    keys = {c["key"] for c in resp.json()["conditions"]}
    assert keys == {"admission"}


def test_checklist_requires_auth(client):
    resp = client.get("/api/condition-checklist/" + "a" * 32)
    assert resp.status_code in (401, 403)
