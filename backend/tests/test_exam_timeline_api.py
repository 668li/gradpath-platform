"""M2 API 契约测试 — /api/civil-service/timeline（C1–C7 + 错误语义）。

契约铁律（contracts/timeline-api.md）：
- 示例日期不硬编——断言一律"取写入值回读比对"；
- UNKNOWN ⇒ planned_date==null && predict_basis==null（响应模型级负断言）；
- 401/404/409/422 语义全覆盖。
"""

from datetime import date

import pytest

from app.models.exam_timeline import DateStatus, NodeStage
from app.services import timeline_service as tl

# 复用证据闸测试里的真实公告正文夹具（本地文件，不打外网）
_GOOD_BODY = (
    "<html><body>"
    "<p>中央机关及其直属机构2026年度考试录用公务员公告，根据公务员法和《公务员录用规定》组织实施。</p>"
    * 30
    + "<p>报考者可于2025年10月15日8:00至10月24日18:00期间登录专题网站进行报名并提交报考申请。</p></body></html>"
).encode()


def _fetch_ok(url):
    return 200, _GOOD_BODY


@pytest.fixture
def seeded(db_session):
    """零提案骨架：3 考次 ×12 节点全 UNKNOWN。"""
    from app.seed.seed_exam_timeline import seed_exam_timeline

    summary = seed_exam_timeline(db_session)
    assert summary["official_without_evidence"] == 0
    return db_session


@pytest.fixture
def user_id(client, db_session):
    """auth_headers 会注册 test@example.com——取回其 id。"""
    client.post(
        "/api/auth/register",
        json={"email": "test@example.com", "password": "Test1234!", "name": "测试用户"},
    )
    from app.models.user import User

    return str(db_session.query(User).filter(User.email == "test@example.com").first().id)


def _evidence_registration(db_session):
    """给 2026 报名节点过闸写 OFFICIAL 并推导 2027 预测，返回 (node26, node27)。"""
    exams = {e.code: e for e in db_session.query(tl.Exam).all()}
    e26, e27 = exams["guokao-2026"], exams["guokao-2027"]
    reg26 = next(n for n in e26.nodes if n.stage_key == NodeStage.registration)
    tl.apply_evidence_date(
        db_session,
        reg26,
        on_date=date(2025, 10, 15),
        end_date=date(2025, 10, 24),
        source_url="https://www.beijing.gov.cn/x",
        fetcher=_fetch_ok,
    )
    tl.derive_predicted_next_year(db_session, e27, e26)
    db_session.commit()
    reg27 = next(n for n in e27.nodes if n.stage_key == NodeStage.registration)
    return reg26, reg27


# ---------------------------------------------------------------- C1/C2


def test_c1_exams_public_list(client, seeded):
    r = client.get("/api/civil-service/timeline/exams")
    assert r.status_code == 200
    codes = {x["code"] for x in r.json()}
    assert {"guokao-2026", "guokao-2027", "guangdong-shengkao-2026"} <= codes
    assert all("next_node" in x for x in r.json())


def test_c2_detail_12_nodes_and_unknown_negatives(client, seeded):
    r = client.get("/api/civil-service/timeline/exams/guokao-2027")
    assert r.status_code == 200
    body = r.json()
    assert len(body["nodes"]) == 12
    for n in body["nodes"]:
        # 零证据世界：全 UNKNOWN 且诚实字段必空
        assert n["date_status"] == "UNKNOWN"
        assert n["planned_date"] is None
        assert n["predict_basis"] is None
        assert n["evidence_id"] is None
        assert n["verifiable"] is False


def test_c2_honest_fields_exposed_after_evidence(client, seeded):
    reg26, reg27 = _evidence_registration(seeded)
    body = client.get("/api/civil-service/timeline/exams/guokao-2026").json()
    n26 = next(x for x in body["nodes"] if x["stage_key"] == "registration")
    assert n26["date_status"] == "OFFICIAL"
    assert n26["planned_date"] == "2025-10-15"  # 回读写入值，非硬编预期
    assert n26["source_url"] and n26["evidence_id"] and n26["collected_at"]
    assert n26["verifiable"] is True
    body27 = client.get("/api/civil-service/timeline/exams/guokao-2027").json()
    n27 = next(x for x in body27["nodes"] if x["stage_key"] == "registration")
    assert n27["date_status"] == "PREDICTED"
    assert n27["planned_date"] == str(reg27.planned_date)
    assert "证据#" in n27["predict_basis"]
    # 2027 其他无锚点环节仍 UNKNOWN（FR-E6）
    hire27 = next(x for x in body27["nodes"] if x["stage_key"] == "hire")
    assert hire27["date_status"] == "UNKNOWN"


def test_c2_404(client, seeded):
    assert client.get("/api/civil-service/timeline/exams/none-2099").status_code == 404


# ---------------------------------------------------------------- C3/C4


def test_c3_subscribe_auth_and_409(client, seeded, user_id, auth_headers):
    assert client.post("/api/civil-service/timeline/exams/guokao-2027/subscribe").status_code == 401
    r = client.post("/api/civil-service/timeline/exams/guokao-2027/subscribe", headers=auth_headers)
    assert r.status_code == 201
    assert "inapp" in r.json()["notify_channels"]
    assert (
        client.post(
            "/api/civil-service/timeline/exams/guokao-2027/subscribe", headers=auth_headers
        ).status_code
        == 409
    )
    # 退订后可重订（恢复，非新建）
    assert (
        client.delete(
            "/api/civil-service/timeline/exams/guokao-2027/subscription", headers=auth_headers
        ).status_code
        == 204
    )
    r2 = client.post(
        "/api/civil-service/timeline/exams/guokao-2027/subscribe", headers=auth_headers
    )
    assert r2.status_code == 201


def test_c4_unsubscribe_without_sub_404(client, seeded, auth_headers):
    assert (
        client.delete(
            "/api/civil-service/timeline/exams/guokao-2026/subscription", headers=auth_headers
        ).status_code
        == 404
    )


# ---------------------------------------------------------------- C6/C5


def _node_id(client, code, stage):
    body = client.get(f"/api/civil-service/timeline/exams/{code}").json()
    return next(x["id"] for x in body["nodes"] if x["stage_key"] == stage)


def test_c6_feedback_flow_and_guard(client, seeded, auth_headers):
    node = _node_id(client, "guokao-2027", "registration")
    # 未订阅 → 404（防探测统一语义）
    r = client.put(
        f"/api/civil-service/timeline/nodes/{node}/feedback",
        json={"status": "done"},
        headers=auth_headers,
    )
    assert r.status_code == 404
    client.post("/api/civil-service/timeline/exams/guokao-2027/subscribe", headers=auth_headers)
    r = client.put(
        f"/api/civil-service/timeline/nodes/{node}/feedback",
        json={"status": "done"},
        headers=auth_headers,
    )
    assert r.status_code == 200
    assert r.json()["stage_key"] == "registration"
    # 改状态=覆盖（unique(sub,node) 更新非新建）
    r2 = client.put(
        f"/api/civil-service/timeline/nodes/{node}/feedback",
        json={"status": "uncertain"},
        headers=auth_headers,
    )
    assert r2.status_code == 200
    # 跨考写回 → 404
    other = _node_id(client, "guangdong-shengkao-2026", "written")
    r3 = client.put(
        f"/api/civil-service/timeline/nodes/{other}/feedback",
        json={"status": "done"},
        headers=auth_headers,
    )
    assert r3.status_code == 404
    # 非法 status → 422
    r4 = client.put(
        f"/api/civil-service/timeline/nodes/{node}/feedback",
        json={"status": "half-done"},
        headers=auth_headers,
    )
    assert r4.status_code == 422


def test_c5_me_progress(client, seeded, auth_headers):
    reg26, _ = _evidence_registration(seeded)  # 让报名窗口成为已过窗节点
    assert reg26.date_status == DateStatus.OFFICIAL
    client.post("/api/civil-service/timeline/exams/guokao-2026/subscribe", headers=auth_headers)
    node = _node_id(client, "guokao-2026", "registration")
    client.put(
        f"/api/civil-service/timeline/nodes/{node}/feedback",
        json={"status": "done"},
        headers=auth_headers,
    )
    r = client.get("/api/civil-service/timeline/me", headers=auth_headers)
    assert r.status_code == 200
    item = next(x for x in r.json() if x["exam"]["code"] == "guokao-2026")
    assert item["subscribed"] is True
    assert item["progress"]["reached"] >= 1
    assert item["progress"]["done"] == 1
    assert client.get("/api/civil-service/timeline/me").status_code == 401


def test_c7_node_public_and_404(client, seeded):
    node = _node_id(client, "guokao-2026", "written")
    r = client.get(f"/api/civil-service/timeline/nodes/{node}")
    assert r.status_code == 200
    assert r.json()["stage_key"] == "written"
    assert client.get("/api/civil-service/timeline/nodes/not-a-uuid").status_code == 404
    assert (
        client.get(
            "/api/civil-service/timeline/nodes/00000000-0000-0000-0000-000000000000"
        ).status_code
        == 404
    )
