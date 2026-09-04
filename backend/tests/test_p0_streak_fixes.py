"""P0 三修测试：

- P0-1: 打开 dashboard 不再产生任何连击记录（删除假打卡）
- P0-2: 真实行为（action checkin / micro action complete_task）写穿全局 StreakRecord
- P0-3: 完成微行动任务允许不填 user_response
"""

from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

from app.models.action_center import DailyAction
from app.models.streak import StreakRecord
from app.models.user import User


def _get_user(db_session) -> User:
    return db_session.query(User).filter(User.email == "test@example.com").first()


# ======================================================================
# P0-1: 打开 dashboard 不触发打卡
# ======================================================================


def test_dashboard_overview_does_not_create_streak_record(auth_headers, client, db_session):
    """打开看板即打卡是假数据：get_overview 不得产生 StreakRecord。"""
    user = _get_user(db_session)

    resp = client.get("/api/dashboard/overview", headers=auth_headers)
    assert resp.status_code == 200

    # 连续访问两次（缓存命中路径也不得打卡）
    resp2 = client.get("/api/dashboard/overview", headers=auth_headers)
    assert resp2.status_code == 200

    records = (
        db_session.query(StreakRecord).filter(StreakRecord.user_id == user.id).all()
    )
    assert records == [], "打开 dashboard 不应产生任何连击记录"


# ======================================================================
# P0-2: 真实行为写穿 StreakRecord
# ======================================================================


def _make_action(db_session, user_id, action_type: str = "study") -> DailyAction:
    action = DailyAction(
        user_id=user_id,
        action_type=action_type,
        title="完成一次真实行动",
        due_date=date.today(),
        status="PENDING",
    )
    db_session.add(action)
    db_session.commit()
    db_session.refresh(action)
    return action


def test_action_checkin_writes_streak_record(auth_headers, client, db_session):
    """行动打卡（action checkin）后当日 StreakRecord 必须有记录。"""
    user = _get_user(db_session)
    action = _make_action(db_session, user.id)

    resp = client.post(
        f"/api/actions/{action.id}/checkin",
        headers=auth_headers,
        json={
            "action_id": action.id,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "note": "",
        },
    )
    assert resp.status_code == 200, resp.text

    record = (
        db_session.query(StreakRecord)
        .filter(
            StreakRecord.user_id == user.id,
            StreakRecord.activity_date == date.today(),
        )
        .first()
    )
    assert record is not None, "action checkin 后当日 StreakRecord 应存在（写穿）"


def test_micro_action_complete_writes_streak_record(auth_headers, client, db_session):
    """完成微行动任务（complete_task）后当日 StreakRecord 必须有记录。"""
    user = _get_user(db_session)

    resp = client.post(
        "/api/micro-actions/plans",
        headers=auth_headers,
        json={"target_path": "employment"},
    )
    assert resp.status_code == 201, resp.text
    plan = resp.json()
    first_task = plan["tasks"][0]

    resp = client.post(
        f"/api/micro-actions/tasks/{first_task['id']}/complete",
        headers=auth_headers,
        json={"user_response": "今天完成了 JD 调研"},
    )
    assert resp.status_code == 200, resp.text

    record = (
        db_session.query(StreakRecord)
        .filter(
            StreakRecord.user_id == user.id,
            StreakRecord.activity_date == date.today(),
        )
        .first()
    )
    assert record is not None, "micro action complete 后当日 StreakRecord 应存在（写穿）"


# ======================================================================
# P0-3: 允许不写字完成任务
# ======================================================================


def test_micro_action_complete_with_empty_response(auth_headers, client, db_session):
    """user_response 传空串也应 200（模型列本可空，service 有兜底文案）。"""
    resp = client.post(
        "/api/micro-actions/plans",
        headers=auth_headers,
        json={"target_path": "employment"},
    )
    assert resp.status_code == 201, resp.text
    plan = resp.json()
    first_task = plan["tasks"][0]

    resp = client.post(
        f"/api/micro-actions/tasks/{first_task['id']}/complete",
        headers=auth_headers,
        json={"user_response": ""},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "completed"
    assert data["user_response"] == ""
