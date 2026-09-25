"""复盘深化测试 — 原则库 / Try 行动卡 / 事实回放（2026-09-25）。

覆盖：
- replay 四源聚合（纯 DB、空数据不炸）
- 原则 CRUD + 空话闸 + 验证状态机 + 冷启动示例
- 行动卡 ≤3 条铁律 + 复审四态 + effective 升级原则闭环
- 静态路由不被 /{retro_id} 吞（FastAPI 注册顺序回归锚点）
"""

from datetime import date, timedelta


def _create_retro(client, headers, title="9月模考复盘") -> str:
    resp = client.post(
        "/api/retrospectives",
        headers=headers,
        json={
            "period_type": "custom",
            "period_start": "2026-09-01",
            "period_end": "2026-09-20",
            "title": title,
            "achievements": ["数学提分10分"],
            "challenges": "时间分配失控",
            "lessons_learned": "大题时间管理是主要失分点",
            "next_steps": ["练习限时套卷"],
            "satisfaction": 3,
        },
    )
    assert resp.status_code == 201
    return resp.json()["id"]


# ----------------------------------------------------------------------
# replay
# ----------------------------------------------------------------------


def test_replay_empty_sources(auth_headers, client):
    """四源全空 → 结构完整不炸，counts 归零。"""
    resp = client.get(
        "/api/retrospectives/replay?period_start=2026-09-01&period_end=2026-09-20",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["counts"]["events"] == 0
    assert isinstance(data["node_feedbacks"], list)
    assert isinstance(data["due_actions"], list)


def test_replay_includes_career_events(auth_headers, client):
    client.post(
        "/api/events",
        headers=auth_headers,
        json={
            "event_date": "2026-09-10",
            "event_type": "project_done",
            "title": "第一次全真模考",
            "situation": "数学时间失控",
        },
    )
    resp = client.get(
        "/api/retrospectives/replay?period_start=2026-09-01&period_end=2026-09-20",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    events = resp.json()["career_events"]
    assert len(events) == 1
    assert events[0]["title"] == "第一次全真模考"
    assert events[0]["has_star"] is True


def test_replay_period_validation(auth_headers, client):
    resp = client.get(
        "/api/retrospectives/replay?period_start=2026-09-20&period_end=2026-09-01",
        headers=auth_headers,
    )
    assert resp.status_code == 422


# ----------------------------------------------------------------------
# 原则库
# ----------------------------------------------------------------------


def test_principles_cold_start_seeds_examples(auth_headers, client):
    """首次访问自动预置示例（破冷启动），带 example 标记。"""
    resp = client.get("/api/retrospectives/principles", headers=auth_headers)
    assert resp.status_code == 200
    principles = resp.json()["principles"]
    assert len(principles) >= 5
    assert all(p["is_example"] for p in principles)


def test_create_principle_with_vague_action_rejected(auth_headers, client):
    """空话闸：'要更加努力学习'式长空话 → 422（命中 service 层空话闸而非长度闸）。"""
    resp = client.post(
        "/api/retrospectives/principles",
        headers=auth_headers,
        json={
            "trigger_scene": "当模考数学大题时间失控的时候",
            "action": "要更加努力学习争取下次考好",
            "scene_tags": ["模考崩盘"],
        },
    )
    assert resp.status_code == 422
    detail = str(resp.json()["detail"])
    assert "空话" in detail or "具体" in detail


def test_create_and_verify_principle_lifecycle(auth_headers, client):
    retro_id = _create_retro(client, auth_headers)
    resp = client.post(
        "/api/retrospectives/principles",
        headers=auth_headers,
        json={
            "trigger_scene": "当数学大题时间快失控的时候",
            "action": "先跳过大题最后一问，把后面两道大题第一问拿到手再回头",
            "rationale": "先收割确定分值",
            "scene_tags": ["模考崩盘"],
            "source_retro_id": retro_id,
        },
    )
    assert resp.status_code == 201
    p = resp.json()
    assert p["status"] == "draft"  # 新原则默认草稿（联想纪律）
    assert p["source_title"] == "9月模考复盘"  # 来源案例快照

    # 复审 again → verified + verify_count=1
    resp = client.post(
        f"/api/retrospectives/principles/{p['id']}/verify",
        headers=auth_headers,
        json={"verdict": "again", "note": "这次真用上了"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "verified"
    assert resp.json()["verify_count"] == 1

    # 修订 → 回 draft 重验
    resp = client.patch(
        f"/api/retrospectives/principles/{p['id']}",
        headers=auth_headers,
        json={"action": "限时训练时每道大题先看分值分配时间"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "draft"


def test_update_principle_vague_rejected(auth_headers, client):
    resp = client.post(
        "/api/retrospectives/principles",
        headers=auth_headers,
        json={
            "trigger_scene": "当连续三天没学习的时候",
            "action": "只做10分钟最小任务就算今天赢",
        },
    )
    pid = resp.json()["id"]
    resp = client.patch(
        f"/api/retrospectives/principles/{pid}",
        headers=auth_headers,
        json={"action": "加油坚持"},
    )
    assert resp.status_code == 422


def test_delete_principle_soft(auth_headers, client):
    resp = client.post(
        "/api/retrospectives/principles",
        headers=auth_headers,
        json={
            "trigger_scene": "当想放弃的时候",
            "action": "写下三个已经完成的进度再决定",
        },
    )
    pid = resp.json()["id"]
    resp = client.delete(f"/api/retrospectives/principles/{pid}", headers=auth_headers)
    assert resp.status_code == 204
    names = [p["id"] for p in client.get(
        "/api/retrospectives/principles", headers=auth_headers
    ).json()["principles"]]
    assert pid not in names


# ----------------------------------------------------------------------
# Try 行动卡
# ----------------------------------------------------------------------


def test_actions_max_three_enforced(auth_headers, client):
    retro_id = _create_retro(client, auth_headers)
    resp = client.post(
        "/api/retrospectives/actions",
        headers=auth_headers,
        json={
            "retro_id": retro_id,
            "items": [
                {"content": f"实验动作{i}", "trigger_scene": f"当场景{i}的时候"} for i in range(4)
            ],
        },
    )
    assert resp.status_code == 422
    assert "3" in str(resp.json()["detail"])


def test_action_review_effective_upgrades_to_principle(auth_headers, client):
    """复审 effective → 自动升级为已验证原则（闭环锚点测试）。"""
    retro_id = _create_retro(client, auth_headers)
    resp = client.post(
        "/api/retrospectives/actions",
        headers=auth_headers,
        json={
            "retro_id": retro_id,
            "items": [
                {
                    "content": "每套卷先花2分钟做分值-时间分配表",
                    "trigger_scene": "当做限时套卷的时候",
                }
            ],
        },
    )
    assert resp.status_code == 201
    action = resp.json()["actions"][0]
    assert action["status"] == "pending"
    assert action["review_due_at"] == (date.today() + timedelta(days=14)).isoformat()

    # 到期列表能看到它（review_due_at 在未来，看未来 14 天窗口）
    resp = client.get(
        "/api/retrospectives/actions/due?include_future_days=14", headers=auth_headers
    )
    assert resp.status_code == 200
    assert any(a["id"] == action["id"] for a in resp.json()["actions"])

    # 复审 effective
    resp = client.post(
        f"/api/retrospectives/actions/{action['id']}/review",
        headers=auth_headers,
        json={"verdict": "effective", "note": "用了，分数稳了"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["action"]["status"] == "effective"
    assert body["upgraded_principle"] is not None
    assert body["upgraded_principle"]["status"] == "verified"
    assert body["upgraded_principle"]["verify_count"] == 1


def test_action_review_not_met_postpones(auth_headers, client):
    retro_id = _create_retro(client, auth_headers, title="十月复盘")
    resp = client.post(
        "/api/retrospectives/actions",
        headers=auth_headers,
        json={
            "retro_id": retro_id,
            "items": [{"content": "面试前一晚写三题提纲", "trigger_scene": "当面试前一晚的时候"}],
        },
    )
    action_id = resp.json()["actions"][0]["id"]
    resp = client.post(
        f"/api/retrospectives/actions/{action_id}/review",
        headers=auth_headers,
        json={"verdict": "not_met"},
    )
    assert resp.status_code == 200
    a = resp.json()["action"]
    assert a["status"] == "pending"  # not_met 保持 pending 但顺延
    assert a["review_due_at"] == (date.today() + timedelta(days=14)).isoformat()


def test_action_vague_content_rejected(auth_headers, client):
    retro_id = _create_retro(client, auth_headers)
    resp = client.post(
        "/api/retrospectives/actions",
        headers=auth_headers,
        json={
            "retro_id": retro_id,
            "items": [{"content": "要认真", "trigger_scene": "当学习的时候"}],
        },
    )
    assert resp.status_code == 422


# ----------------------------------------------------------------------
# 路由顺序回归锚点：静态段不被 /{retro_id} 吞
# ----------------------------------------------------------------------


def test_static_routes_not_swallowed_by_uuid_route(auth_headers, client):
    """principles/actions/replay 必须命中静态路由而非 422 UUID 转换失败。"""
    assert (
        client.get("/api/retrospectives/principles", headers=auth_headers).status_code == 200
    )
    assert (
        client.get(
            "/api/retrospectives/actions/due", headers=auth_headers
        ).status_code
        == 200
    )


# ----------------------------------------------------------------------
# chat 注入（对抗审查硬性验收：主对话必须能看到原则）
# ----------------------------------------------------------------------


def test_principles_injected_into_chat_context(auth_headers, client, db_session):
    """建原则后 build_user_context 必须含【个人原则】段。"""
    from app.services.retro_principle_service import create_principle

    # 取当前登录用户 id
    me = client.get("/api/auth/me", headers=auth_headers)
    user_id = me.json()["id"]

    create_principle(
        db_session,
        user_id,
        trigger_scene="当数学大题时间快失控的时候",
        action="先跳过最后一问收割后面确定分值",
        rationale=None,
        scene_tags=["模考崩盘"],
        source_retro_id=None,
    )

    from app.core.cache import invalidate_user_context

    invalidate_user_context(str(user_id))  # 穿透缓存（写入路径已自动失效，此处显式确保）

    from app.services.chat_service import build_user_context

    ctx = build_user_context(db_session, user_id)
    assert "【个人原则" in ctx
    assert "先跳过最后一问" in ctx
    assert "模考崩盘" in ctx or "当数学大题" in ctx


def test_principles_chat_injection_excludes_invalid(auth_headers, client, db_session):
    me = client.get("/api/auth/me", headers=auth_headers)
    user_id = me.json()["id"]
    from app.services.retro_principle_service import (
        create_principle,
        get_principles_for_chat,
        verify_principle,
    )

    p, _ = create_principle(
        db_session,
        user_id,
        trigger_scene="当出分落差想立刻决定的时候",
        action="强制等48小时只收集信息不做动作",
        rationale=None,
        scene_tags=[],
        source_retro_id=None,
    )
    verify_principle(db_session, user_id, p.id, "ineffective")
    lines = get_principles_for_chat(db_session, user_id)
    assert all("48小时" not in l["line"] for l in lines)  # 失效原则不注入
