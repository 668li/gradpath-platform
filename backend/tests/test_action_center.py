# backend/tests/test_action_center.py
"""行动任务中心 API 测试 — 认证 / 今日清单 / 创建(幂等) / 更新 / 打卡 / 连击 / 权重。"""

from datetime import datetime, timedelta, timezone

# ----------------------------------------------------------------------
# 辅助函数
# ----------------------------------------------------------------------
def _today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _create_action(client, auth_headers, action_type="read_article", title="读一篇行业文章", due_date=None, idempotency=None):
    headers = dict(auth_headers)
    if idempotency:
        headers["X-Idempotency-Key"] = idempotency
    resp = client.post(
        "/api/actions",
        headers=headers,
        json={
            "action_type": action_type,
            "title": title,
            "due_date": due_date or _today(),
        },
    )
    assert resp.status_code == 200, f"创建行动失败: {resp.text}"
    return resp.json()


def _checkin(client, auth_headers, action_id, completed_at=None, idempotency=None, **extra):
    headers = dict(auth_headers)
    if idempotency:
        headers["X-Idempotency-Key"] = idempotency
    resp = client.post(
        f"/api/actions/{action_id}/checkin",
        headers=headers,
        json={
            "action_id": action_id,
            "completed_at": completed_at or datetime.now(timezone.utc).isoformat(),
            **extra,
        },
    )
    return resp


# ----------------------------------------------------------------------
# 认证要求
# ----------------------------------------------------------------------
class TestAuthRequired:
    def test_today_requires_auth(self, client):
        assert client.get("/api/actions/today").status_code == 401

    def test_create_requires_auth(self, client):
        resp = client.post(
            "/api/actions",
            json={"action_type": "read_article", "title": "x", "due_date": _today()},
        )
        assert resp.status_code == 401

    def test_checkin_requires_auth(self, client):
        resp = client.post(
            "/api/actions/1/checkin",
            json={"action_id": 1, "completed_at": datetime.now(timezone.utc).isoformat()},
        )
        assert resp.status_code == 401

    def test_streak_requires_auth(self, client):
        assert client.get("/api/actions/streaks").status_code == 401

    def test_weights_requires_auth(self, client):
        assert client.get("/api/actions/weights").status_code == 401


# ----------------------------------------------------------------------
# 创建行动
# ----------------------------------------------------------------------
class TestCreateAction:
    def test_create_ok(self, auth_headers, client):
        action = _create_action(client, auth_headers, action_type="mock_interview", title="模拟面试练习")
        assert action["id"]
        assert action["user_id"]  # UUID 已注入
        assert action["action_type"] == "mock_interview"
        assert action["title"] == "模拟面试练习"
        assert action["due_date"] == _today()
        assert action["status"] == "PENDING"
        assert action["weight"] == 15  # 来自种子权重表

    def test_weight_from_seed_table(self, auth_headers, client):
        """不同 action_type 权重来自 t_action_weight 种子。"""
        assert _create_action(client, auth_headers, action_type="get_offer")["weight"] == 100
        assert _create_action(client, auth_headers, action_type="custom")["weight"] == 1

    def test_duplicate_same_day_type_conflict(self, auth_headers, client):
        _create_action(client, auth_headers, action_type="read_article")
        resp = client.post(
            "/api/actions",
            headers=auth_headers,
            json={"action_type": "read_article", "title": "重复", "due_date": _today()},
        )
        assert resp.status_code == 409

    def test_idempotency_key_returns_same_action(self, auth_headers, client):
        first = _create_action(client, auth_headers, idempotency="req-001")
        second = _create_action(client, auth_headers, idempotency="req-001")
        assert first["id"] == second["id"]

    def test_note_biz_fields_ignored(self, auth_headers, client):
        """note / biz_fields 契约无存储列，创建不报错且忽略。"""
        resp = client.post(
            "/api/actions",
            headers=auth_headers,
            json={
                "action_type": "read_article",
                "title": "x",
                "due_date": _today(),
                "note": "备注不落库",
                "biz_fields": {"k": "v"},
            },
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "x"


# ----------------------------------------------------------------------
# 今日行动清单
# ----------------------------------------------------------------------
class TestTodayList:
    def test_empty_list(self, auth_headers, client):
        resp = client.get("/api/actions/today", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["items"] == []
        assert body["total"] == 0

    def test_sorted_by_weight_desc(self, auth_headers, client):
        _create_action(client, auth_headers, action_type="read_article")  # weight 1
        _create_action(client, auth_headers, action_type="mock_interview")  # weight 15
        resp = client.get("/api/actions/today", headers=auth_headers)
        items = resp.json()["items"]
        assert [i["action_type"] for i in items] == ["mock_interview", "read_article"]

    def test_only_today_actions(self, auth_headers, client):
        yesterday = (datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat()
        _create_action(client, auth_headers, due_date=yesterday)
        _create_action(client, auth_headers, action_type="finish_course")
        resp = client.get("/api/actions/today", headers=auth_headers)
        items = resp.json()["items"]
        assert len(items) == 1
        assert items[0]["action_type"] == "finish_course"

    def test_user_isolation(self, auth_headers, client):
        """其他用户的行动不出现。"""
        # 注册第二个用户
        client.post(
            "/api/auth/register",
            json={"email": "other@example.com", "password": "Test1234!", "name": "其他用户"},
        )
        resp2 = client.post(
            "/api/auth/login",
            json={"email": "other@example.com", "password": "Test1234!"},
        )
        other_headers = {"Authorization": f"Bearer {resp2.json()['access_token']}"}
        _create_action(client, other_headers)

        resp = client.get("/api/actions/today", headers=auth_headers)
        assert resp.json()["total"] == 0


# ----------------------------------------------------------------------
# 更新行动
# ----------------------------------------------------------------------
class TestUpdateAction:
    def test_update_title_and_status(self, auth_headers, client):
        action = _create_action(client, auth_headers)
        resp = client.put(
            f"/api/actions/{action['id']}",
            headers=auth_headers,
            json={"title": "改后的标题", "status": "CANCELED"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["title"] == "改后的标题"
        assert body["status"] == "CANCELED"

    def test_update_nonexistent_404(self, auth_headers, client):
        resp = client.put(
            "/api/actions/999999", headers=auth_headers, json={"title": "x"}
        )
        assert resp.status_code == 404

    def test_note_ignored_on_update(self, auth_headers, client):
        action = _create_action(client, auth_headers)
        resp = client.put(
            f"/api/actions/{action['id']}",
            headers=auth_headers,
            json={"title": "t", "note": "不落库"},
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "t"


# ----------------------------------------------------------------------
# 行动打卡（幂等 + 连击）
# ----------------------------------------------------------------------
class TestCheckin:
    def test_checkin_ok(self, auth_headers, client):
        action = _create_action(client, auth_headers)
        resp = _checkin(client, auth_headers, action["id"], note="已完成", evidence_url="https://example.com/ev")
        assert resp.status_code == 200, resp.text
        checkin = resp.json()
        assert checkin["action_id"] == action["id"]
        assert checkin["biz_req_no"]
        assert checkin["note"] == "已完成"

        # 行动状态置 DONE
        resp = client.get("/api/actions/today", headers=auth_headers)
        assert resp.json()["items"][0]["status"] == "DONE"

    def test_checkin_idempotent(self, auth_headers, client):
        action = _create_action(client, auth_headers)
        resp1 = _checkin(client, auth_headers, action["id"], idempotency="checkin-001")
        resp2 = _checkin(client, auth_headers, action["id"], idempotency="checkin-001")
        assert resp1.status_code == 200
        assert resp2.status_code == 200
        assert resp1.json()["id"] == resp2.json()["id"]

    def test_checkin_nonexistent_action_404(self, auth_headers, client):
        resp = _checkin(client, auth_headers, 999999)
        assert resp.status_code == 404

    def test_checkin_history(self, auth_headers, client):
        action = _create_action(client, auth_headers)
        _checkin(client, auth_headers, action["id"], idempotency="ch-1")
        _checkin(client, auth_headers, action["id"], idempotency="ch-2")
        resp = client.get(f"/api/actions/{action['id']}/checkins", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 2
        assert len(body["items"]) == 2


# ----------------------------------------------------------------------
# 连击统计
# ----------------------------------------------------------------------
class TestStreak:
    def test_never_when_no_checkin(self, auth_headers, client):
        resp = client.get("/api/actions/streaks", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["streak_status"] == "NEVER"
        assert body["current_streak_days"] == 0

    def test_active_after_first_checkin(self, auth_headers, client):
        action = _create_action(client, auth_headers)
        _checkin(client, auth_headers, action["id"])
        resp = client.get("/api/actions/streaks", headers=auth_headers)
        body = resp.json()
        assert body["current_streak_days"] == 1
        assert body["longest_streak_days"] == 1
        assert body["streak_status"] == "ACTIVE"

    def test_consecutive_days_increment(self, auth_headers, client):
        """连续两天打卡 → current=2；中断后重开 → current 归 1。"""
        a1 = _create_action(client, auth_headers)
        a2 = _create_action(client, auth_headers, action_type="finish_course")
        a3 = _create_action(client, auth_headers, action_type="resume_revise")
        today = datetime.now(timezone.utc)

        # 前天 + 昨天连续 → current=2
        _checkin(
            client, auth_headers, a1["id"],
            completed_at=(today - timedelta(days=2)).isoformat(),
        )
        _checkin(
            client, auth_headers, a2["id"],
            completed_at=(today - timedelta(days=1)).isoformat(),
        )
        body = client.get("/api/actions/streaks", headers=auth_headers).json()
        assert body["current_streak_days"] == 2
        assert body["longest_streak_days"] == 2
        assert body["streak_status"] == "ACTIVE"

        # 中断：隔 2 天（今天-4）再打卡 → 重开为 1，状态 BROKEN
        _checkin(
            client, auth_headers, a3["id"],
            completed_at=(today - timedelta(days=4)).isoformat(),
        )
        body = client.get("/api/actions/streaks", headers=auth_headers).json()
        assert body["current_streak_days"] == 1
        assert body["streak_status"] == "BROKEN"

    def test_checkin_writes_growth_trajectory(self, auth_headers, client):
        """打卡联动写入成长轨迹（event_type=action_checkin）。"""
        action = _create_action(client, auth_headers)
        _checkin(client, auth_headers, action["id"], idempotency="ch-traj")
        resp = client.get("/api/growth/trajectory", headers=auth_headers)
        items = resp.json()["items"]
        assert len(items) == 1
        assert items[0]["event_type"] == "action_checkin"
        assert items[0]["event_payload"]["action_id"] == action["id"]
        assert items[0]["source_event_id"] == "ch-traj"


# ----------------------------------------------------------------------
# 行动权重表
# ----------------------------------------------------------------------
class TestWeights:
    def test_seeded_weights(self, auth_headers, client):
        resp = client.get("/api/actions/weights", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 7
        by_type = {w["action_type"]: w["weight"] for w in body["items"]}
        assert by_type["read_article"] == 1
        assert by_type["mock_interview"] == 15
        assert by_type["get_offer"] == 100
