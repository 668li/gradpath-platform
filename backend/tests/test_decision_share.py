# backend/tests/test_decision_share.py
"""决策报告公开分享测试。

覆盖：
- share 需要登录（401）
- token 生成往返：analyze → share → 公开端点可读
- share 幂等：重复调用复用同一 token
- 公开端点匿名化：不含用户名/邮箱/结果回传个人数据
- 无效 token → 404
- 别人的记录不能 share（404）
"""

from uuid import uuid4

from app.models.path_comparison import PathComparison
from app.models.user import User
from app.services.path_comparison_service import save_comparison


def _current_user_id(db) -> object:
    """auth_headers 注册的 test@example.com 用户的 id。"""
    user = db.query(User).filter(User.email == "test@example.com").one()
    return user.id


def _make_record(db, user_id, *, kaoyan_estimated_score: int | None = 345) -> PathComparison:
    """直接落库一条决策记录（不走 analyze，专注 share 逻辑）。"""
    comparison_result = {
        "metrics": [
            {
                "path_type": "kaoyan",
                "target_role": "计算机技术",
                "match_score": 0.8,
                "income_1y": "暂无相关数据",
                "pros": [],
                "cons": [],
                "evidence": [],
            }
        ],
        "recommendation": "建议以考研为主，冲刺与保底并行。",
        "input": {
            "major": "计算机",
            "region": "广东",
            "graduation_year": 2027,
            "kaoyan_estimated_score": kaoyan_estimated_score,
        },
        "position_analysis": None,
        "school_analysis": None,
    }
    return save_comparison(
        db=db,
        user_id=user_id,
        paths=[{"path_type": "kaoyan", "target_role": "计算机技术"}],
        comparison_result=comparison_result,
        user_context={"input": comparison_result["input"]},
    )


def test_share_requires_auth(client, db_session):
    record = _make_record(db_session, uuid4())
    resp = client.post(f"/api/path-decision/{record.id}/share")
    assert resp.status_code == 401


def test_share_roundtrip(client, auth_headers, db_session):
    record = _make_record(db_session, _current_user_id(db_session))
    resp = client.post(f"/api/path-decision/{record.id}/share", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    token = resp.json()["token"]
    assert token and len(token) >= 32
    assert resp.json()["url"] == f"/share/decision/{token}"

    # 公开端点（无需登录）可读到匿名化报告
    public = client.get(f"/api/share/decision/{token}")
    assert public.status_code == 200, public.text
    body = public.json()
    assert body["id"] == str(record.id)
    assert body["recommendation"]
    assert body["metrics"]
    assert body["input"]["major"] == "计算机"
    assert body["input"]["kaoyan_estimated_score"] == 345
    # 空库时 has_data=false（诚实占位，不编造）
    assert body["peer_destinations"]["has_data"] is False
    assert body["peer_destinations"]["distribution"] == []


def test_share_idempotent(client, auth_headers, db_session):
    record = _make_record(db_session, _current_user_id(db_session))
    first = client.post(f"/api/path-decision/{record.id}/share", headers=auth_headers)
    second = client.post(f"/api/path-decision/{record.id}/share", headers=auth_headers)
    assert first.status_code == second.status_code == 200
    assert first.json()["token"] == second.json()["token"]


def test_public_endpoint_anonymized(client, auth_headers, db_session):
    """分享报告不含用户名、邮箱与结果回传个人数据。"""
    record = _make_record(db_session, _current_user_id(db_session))
    token = client.post(f"/api/path-decision/{record.id}/share", headers=auth_headers).json()[
        "token"
    ]

    public = client.get(f"/api/share/decision/{token}")
    assert public.status_code == 200
    text = public.text
    assert "测试用户" not in text
    assert "test@example.com" not in text
    assert "outcome" not in public.json()


def test_invalid_token_returns_404(client):
    resp = client.get("/api/share/decision/not-a-real-token")
    assert resp.status_code == 404


def test_cannot_share_others_record(client, auth_headers, db_session):
    """别人的记录 share → 404（数据隔离）。"""
    other_user_id = uuid4()
    record = _make_record(db_session, other_user_id)
    resp = client.post(f"/api/path-decision/{record.id}/share", headers=auth_headers)
    assert resp.status_code == 404


def test_missing_record_share_404(client, auth_headers):
    resp = client.post(
        f"/api/path-decision/{uuid4()}/share",
        headers=auth_headers,
    )
    assert resp.status_code == 404
