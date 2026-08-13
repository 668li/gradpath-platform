"""多路径 What-If 对比 API — 量化对比多条职业路径。

端点：
- POST /api/path-comparison/compare — 提交 2-3 条路径，生成量化对比
- GET  /api/path-comparison/history  — 获取历史对比记录
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.path_comparison import (
    ComparisonRequest,
    ComparisonResponse,
    PathMetrics,
)
from app.services import path_comparison_service as svc

router = APIRouter(prefix="/api/path-comparison", tags=["多路径对比"])


@router.post("/compare", response_model=ComparisonResponse)
def compare_paths(
    req: ComparisonRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ComparisonResponse:
    """提交 2-3 条路径，生成量化对比并保存为历史记录。

    若用户已有霍兰德测评结果，匹配度将基于 RIASEC 维度计算；
    否则使用预设默认匹配度。
    """
    paths_payload = [{"path_type": p.path_type, "target_role": p.target_role} for p in req.paths]

    user_context = svc.build_user_context(db, user.id)
    comparison = svc.generate_comparison(paths_payload, user_context=user_context)

    record = svc.save_comparison(
        db=db,
        user_id=user.id,
        paths=paths_payload,
        comparison_result=comparison,
        user_context=user_context,
    )

    return ComparisonResponse(
        id=str(record.id),
        metrics=[PathMetrics(**m) for m in comparison["metrics"]],
        recommendation=comparison["recommendation"],
        created_at=record.created_at,
    )


@router.get("/history", response_model=list[ComparisonResponse])
def get_history(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[ComparisonResponse]:
    """获取用户的历史对比记录（按时间倒序）。"""
    records = svc.list_history(db, user.id)
    responses: list[ComparisonResponse] = []
    for r in records:
        data = svc.to_response(r)
        responses.append(ComparisonResponse(
            id=data["id"],
            metrics=[PathMetrics(**m) for m in data["metrics"]],
            recommendation=data["recommendation"],
            created_at=r.created_at,
        ))
    return responses
