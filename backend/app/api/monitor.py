# backend/app/api/monitor.py
"""Monitor API

安全说明 (FASTAPI-AUTH-001 / FASTAPI-AUTHZ-001):
    所有监控端点均会暴露系统内部信息（用户数、帖子数、DB 连接、错误、告警规则等），
    必须强制 admin 鉴权，禁止匿名/普通用户访问。
"""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.deps import get_admin_user
from app.database import get_db
from app.models.user import User

router = APIRouter(prefix="/api/monitor", tags=["monitor"])


@router.get("/metrics")
def get_metrics(
    db: Session = Depends(get_db),
    # FASTAPI-AUTH-001 + FASTAPI-AUTHZ-001: 监控数据仅 admin 可见
    admin: User = Depends(get_admin_user),
):
    sql1 = "SELECT COUNT(*) FROM users"
    sql2 = "SELECT COUNT(*) FROM experience_posts"
    sql3 = "SELECT COUNT(*) FROM qas"
    sql4 = "SELECT COUNT(*) FROM knowledge_articles"
    total_users = db.execute(text(sql1)).scalar()
    total_posts = db.execute(text(sql2)).scalar()
    total_qa = db.execute(text(sql3)).scalar()
    total_knowledge = db.execute(text(sql4)).scalar()
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "users": total_users,
        "experience_posts": total_posts,
        "qa_questions": total_qa,
        "knowledge_articles": total_knowledge,
    }


@router.get("/health")
def health_check(
    db: Session = Depends(get_db),
    # FASTAPI-AUTH-001 + FASTAPI-AUTHZ-001: 健康检查细节仅 admin 可见
    # 注意：公开的存活探针请使用 /health (root) 端点
    admin: User = Depends(get_admin_user),
):
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "disconnected"
    return {
        "status": "ok" if db_status == "connected" else "degraded",
        "database": db_status,
    }


@router.get("/errors")
def get_errors(
    # FASTAPI-AUTH-001 + FASTAPI-AUTHZ-001: 错误信息仅 admin 可见
    admin: User = Depends(get_admin_user),
):
    return {"errors": [], "total": 0}


@router.get("/alerts")
def get_alerts(
    # FASTAPI-AUTH-001 + FASTAPI-AUTHZ-001: 告警信息仅 admin 可见
    admin: User = Depends(get_admin_user),
):
    return {"alerts": [], "active": 0}


@router.get("/alert-rules")
def get_alert_rules(
    # FASTAPI-AUTH-001 + FASTAPI-AUTHZ-001: 告警规则仅 admin 可见
    admin: User = Depends(get_admin_user),
):
    return {"rules": [
        {"name": "response_time", "condition": "> 5s", "action": "notify"},
        {"name": "error_rate", "condition": "> 5pct", "action": "notify"},
    ]}
