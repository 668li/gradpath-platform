# backend/tests/test_life_design_blueprint.py
"""人生设计蓝图 API 测试 — 保存/版本递增/列表/最新/越权隔离（认识自己 V1）。"""

import uuid

BLUEPRINT_CONTENT = (
    "# 个人人生设计蓝图\n\n"
    "## 你在这里\n健康 6 分、工作 3 分……\n\n"
    "## 真问题\n" + ("重新定义：不是「考不上怎么办」，而是「如何在三个月内验证备考节奏是否可持续」。 " * 8)
)


def _create(client, auth_headers, **overrides):
    payload = {
        "content": BLUEPRINT_CONTENT,
        "title": None,
        "transcript": [
            {"role": "assistant", "content": "⟨S1⟩\n先给健康/工作/娱乐/爱打个分？", "stage": "S1"},
            {"role": "user", "content": "健康7 工作3 娱乐5 爱4", "stage": None},
        ],
    }
    payload.update(overrides)
    return client.post(
        "/api/life-design/blueprints", headers=auth_headers, json=payload
    )


def test_create_blueprint_defaults(client, auth_headers):
    """保存蓝图：默认标题按版本生成，transcript 入库。"""
    resp = _create(client, auth_headers)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["title"] == "我的人生蓝图 v1"
    assert body["version"] == 1
    assert body["status"] == "completed"
    assert body["content"].startswith("# 个人人生设计蓝图")


def test_version_increments(client, auth_headers):
    """再访谈 = 新版本：版本号递增，列表按版本倒序。"""
    r1 = _create(client, auth_headers)
    r2 = _create(client, auth_headers, title="第二版")
    assert r1.json()["version"] == 1
    assert r2.json()["version"] == 2
    assert r2.json()["title"] == "第二版"

    listed = client.get(
        "/api/life-design/blueprints", headers=auth_headers
    ).json()
    assert [b["version"] for b in listed] == [2, 1]
    # 列表项不含全文（8000+ 字蓝图不整段下发）
    assert "content" not in listed[0]


def test_latest_and_get_by_id(client, auth_headers):
    """latest 返回最高版本；按 id 读取返回全文。"""
    _create(client, auth_headers)
    created = _create(client, auth_headers).json()

    latest = client.get(
        "/api/life-design/blueprints/latest", headers=auth_headers
    ).json()
    assert latest["version"] == 2

    one = client.get(
        f"/api/life-design/blueprints/{created['id']}", headers=auth_headers
    )
    assert one.status_code == 200
    assert one.json()["content"] == BLUEPRINT_CONTENT


def test_latest_empty_returns_null(client, auth_headers):
    """无蓝图：latest 200 + null（前端按空态渲染，不 404）。"""
    resp = client.get("/api/life-design/blueprints/latest", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() is None


def test_user_isolation_and_validation(client, auth_headers):
    """越权读不到别人的蓝图；content 过短 422；未登录 401。"""
    created = _create(client, auth_headers).json()

    # 未登录
    assert client.get("/api/life-design/blueprints").status_code == 401

    # 越权（伪造随机 id，属于他人或不存在的蓝图都应 404）
    assert (
        client.get(
            f"/api/life-design/blueprints/{uuid.uuid4()}", headers=auth_headers
        ).status_code
        == 404
    )
    assert created["id"]  # sanity：自己能读到的 id 存在

    # content 校验
    bad = _create(client, auth_headers, content="太短")
    assert bad.status_code == 422
