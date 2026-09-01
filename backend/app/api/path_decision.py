"""三路对比决策引擎 API — 用真实数据对比考研/考公/就业三条路。

端点：
- POST /api/path-decision/analyze — 输入学生档案（含个人条件），生成三路对比
- GET  /api/path-decision/history  — 获取历史对比记录（按时间倒序）
- POST /api/path-decision/{decision_id}/outcome — 结果回传（决策飞轮闭环）
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.path_comparison import PathComparison
from app.models.user import User
from app.schemas.path_comparison import (
    DecisionEngineRequest,
    DecisionEngineResponse,
    DecisionOutcomeInfo,
    DecisionOutcomeSubmit,
    OutcomeStats,
    PathMetrics,
    PeerDestinations,
)
from app.services import path_comparison_service, path_decision_engine

router = APIRouter(prefix="/api/path-decision", tags=["三路对比决策引擎"])


def _response_from_record(
    record: PathComparison, db: Session | None = None
) -> DecisionEngineResponse:
    """统一组装响应 — 历史记录与分析结果共用。

    传入 db 时附加同分人群去向（实时聚合，不进缓存）；历史列表不传 db，
    避免每条记录各打一次 outcome_reports 聚合查询。
    """
    result = record.comparison_result or {}
    metrics = result.get("metrics", [])
    outcome = None
    if record.selected_path or record.outcome_status:
        outcome = DecisionOutcomeInfo(
            selected_path=record.selected_path,
            selected_label=record.selected_label,
            outcome_status=record.outcome_status,
            actual_outcome=record.actual_outcome,
            satisfaction=record.satisfaction,
            reviewed_at=record.reviewed_at,
        )
    peer_destinations = None
    if db is not None:
        decision_input = result.get("input") or (record.user_context or {}).get("input") or {}
        kaoyan_score = decision_input.get("kaoyan_estimated_score")
        if kaoyan_score:
            peer_destinations = PeerDestinations(
                **path_comparison_service.build_peer_destinations(db, kaoyan_score)
            )
    return DecisionEngineResponse(
        id=str(record.id),
        metrics=[PathMetrics(**m) for m in metrics],
        recommendation=record.recommendation or result.get("recommendation", ""),
        input=result.get("input", {}),
        position_analysis=result.get("position_analysis"),
        school_analysis=result.get("school_analysis"),
        outcome=outcome,
        peer_destinations=peer_destinations,
        created_at=record.created_at,
    )


@router.post("/analyze", response_model=DecisionEngineResponse)
def analyze_paths(
    req: DecisionEngineRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DecisionEngineResponse:
    """输入学生档案（含个人条件包），生成考研/考公/就业三路对比并保存为历史记录。

    每个指标都来自现有数据库实时聚合，附带溯源证据；无数据时诚实降级。
    个人条件（应届/政治面貌/学历/性别/基层经历/预估分）参与考公可报边界过滤
    与岗位竞争力分级，见响应 position_analysis / school_analysis。
    """
    decision = path_decision_engine.generate_decision(
        db=db,
        major=req.major,
        region=req.region,
        school_tier=req.school_tier,
        graduation_year=req.graduation_year,
        fresh_status=req.fresh_status,
        party_status=req.party_status,
        education=req.education,
        has_grassroots=req.has_grassroots,
        gender=req.gender,
        estimated_score=req.estimated_score,
        kaoyan_estimated_score=req.kaoyan_estimated_score,
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

    return _response_from_record(record, db=db)


@router.post("/{decision_id}/share")
def share_decision(
    decision_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """为决策生成公开分享链接（幂等：已生成则复用）。

    返回 { token, url }，url 形如 /share/decision/{token}。
    分享页渲染匿名化报告，不含用户名与登录信息。
    """
    token = path_comparison_service.create_share_token(db, decision_id, user.id)
    if token is None:
        raise HTTPException(status_code=404, detail="对比记录不存在或不属于当前用户")
    return {"token": token, "url": f"/share/decision/{token}"}


@router.get("/history", response_model=list[DecisionEngineResponse])
def get_history(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[DecisionEngineResponse]:
    """获取用户的三路对比历史记录（按时间倒序，含岗位/院校分析与结果回传状态）。"""
    records = path_comparison_service.list_history(db, user.id)
    responses: list[DecisionEngineResponse] = []
    for r in records:
        result = r.comparison_result or {}
        if not result.get("metrics"):
            continue
        responses.append(_response_from_record(r))
    return responses


@router.post("/{decision_id}/outcome", response_model=DecisionEngineResponse)
def submit_outcome(
    decision_id: str,
    payload: DecisionOutcomeSubmit,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DecisionEngineResponse:
    """结果回传：记录用户「当时选了哪条路、结果如何」，飞轮闭环第一圈。"""
    record = path_comparison_service.submit_outcome(
        db, decision_id, user.id, payload.model_dump(exclude_none=True)
    )
    if record is None:
        raise HTTPException(status_code=404, detail="对比记录不存在或不属于当前用户")
    return _response_from_record(record)


@router.get("/outcome-stats", response_model=OutcomeStats)
def get_outcome_stats(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> OutcomeStats:
    """全站结果回传统计（匿名聚合）— 用于互惠展示：「算法的准，靠大家交回真实结果」。"""
    rows = (
        db.query(PathComparison.selected_path, PathComparison.outcome_status, func.count())
        .filter(
            or_(PathComparison.selected_path.isnot(None), PathComparison.outcome_status.isnot(None))
        )
        .group_by(PathComparison.selected_path, PathComparison.outcome_status)
        .all()
    )
    by_status: dict[str, int] = {}
    by_path: dict[str, int] = {}
    total = 0
    for selected_path, outcome_status, count in rows:
        total += count
        if outcome_status:
            by_status[outcome_status] = by_status.get(outcome_status, 0) + count
        if selected_path:
            by_path[selected_path] = by_path.get(selected_path, 0) + count
    return OutcomeStats(total_outcomes=total, by_status=by_status, by_selected_path=by_path)
