"""三路对比决策引擎 API — 用真实数据对比考研/考公/就业三条路。

端点：
- POST /api/path-decision/analyze — 输入学生档案，生成三路对比（含溯源证据）
- GET  /api/path-decision/history  — 获取历史对比记录（按时间倒序）
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.path_comparison import DecisionEngineRequest, DecisionEngineResponse, PathMetrics
from app.services import path_comparison_service, path_decision_engine

router = APIRouter(prefix="/api/path-decision", tags=["三路对比决策引擎"])


@router.post("/analyze", response_model=DecisionEngineResponse)
def analyze_paths(
    req: DecisionEngineRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DecisionEngineResponse:
    """输入学生档案，生成考研/考公/就业三路对比并保存为历史记录。

    每个指标都来自现有数据库实时聚合，附带溯源证据；无数据时诚实降级。
    """
    decision = path_decision_engine.generate_decision(
        db=db,
        major=req.major,
        region=req.region,
        school_tier=req.school_tier,
        graduation_year=req.graduation_year,
    )

    # 复用 PathComparison 表持久化（JSONB），不新建表
    paths_payload = [
        {"path_type": m["path_type"], "target_role": m["target_role"]} for m in decision["metrics"]
    ]
    record = path_comparison_service.save_comparison(
        db=db,
        user_id=user.id,
        paths=paths_payload,
        comparison_result=decision,
        user_context={"input": decision["input"]},
    )

    return DecisionEngineResponse(
        id=str(record.id),
        metrics=[PathMetrics(**m) for m in decision["metrics"]],
        recommendation=decision["recommendation"],
        input=decision["input"],
        created_at=record.created_at,
    )


@router.get("/history", response_model=list[DecisionEngineResponse])
def get_history(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[DecisionEngineResponse]:
    """获取用户的三路对比历史记录（按时间倒序）。"""
    records = path_comparison_service.list_history(db, user.id)
    responses: list[DecisionEngineResponse] = []
    for r in records:
        result = r.comparison_result or {}
        metrics = result.get("metrics", [])
        if not metrics:
            continue
        responses.append(
            DecisionEngineResponse(
                id=str(r.id),
                metrics=[PathMetrics(**m) for m in metrics],
                recommendation=r.recommendation or result.get("recommendation", ""),
                input=result.get("input", {}),
                created_at=r.created_at,
            )
        )
    return responses
