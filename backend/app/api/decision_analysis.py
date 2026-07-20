"""决策分析 API — 预验尸 + 决策矩阵 + 红队质疑。"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.decision_analysis import (
    DecisionAnalysisCreate,
    DecisionAnalysisResponse,
    MatrixComputeRequest,
    PremortemAnalyzeRequest,
    RedTeamGenerateRequest,
)
from app.services import decision_analysis_service

router = APIRouter(prefix="/api/decision-analysis", tags=["决策深度分析"])


@router.get("/list", response_model=list[DecisionAnalysisResponse])
def list_analyses(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取所有决策分析。"""
    analyses = decision_analysis_service.get_analyses(db, user.id)
    return [DecisionAnalysisResponse.model_validate(a) for a in analyses]


@router.post("/create", response_model=DecisionAnalysisResponse, status_code=status.HTTP_201_CREATED)
def create_analysis(
    body: DecisionAnalysisCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """创建决策分析（自动计算矩阵加权得分）。"""
    data = body.model_dump()
    analysis = decision_analysis_service.create_analysis(db, user.id, data)
    return DecisionAnalysisResponse.model_validate(analysis)


@router.get("/{analysis_id}", response_model=DecisionAnalysisResponse)
def get_analysis(
    analysis_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取单个决策分析。"""
    analysis = decision_analysis_service.get_analysis(db, user.id, analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="分析不存在")
    return DecisionAnalysisResponse.model_validate(analysis)


@router.post("/compute-matrix")
def compute_matrix(body: MatrixComputeRequest):
    """计算决策矩阵加权得分（不保存）。"""
    result = decision_analysis_service.compute_matrix(
        [c.model_dump() for c in body.criteria],
        [o.model_dump() for o in body.matrix_scores],
    )
    return result


@router.post("/premortem-analyze")
async def analyze_premortem(body: PremortemAnalyzeRequest):
    """AI 分析预验尸结果：聚类风险 + 生成保障措施。"""
    return await decision_analysis_service.analyze_premortem(
        body.title, body.options, body.premortem_reasons
    )


@router.post("/red-team-questions")
async def generate_red_team(body: RedTeamGenerateRequest):
    """AI 生成红队质疑问题。"""
    questions = await decision_analysis_service.generate_red_team_questions(
        body.title, body.options, body.reasoning
    )
    return {"questions": questions}


@router.post("/{analysis_id}/ai-analysis")
async def generate_ai_analysis(
    analysis_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """AI 综合分析决策（预验尸+矩阵+红队）。"""
    # 修复 bug: service 层 raise ValueError("分析不存在") -> 500，应转 404
    try:
        analysis = await decision_analysis_service.generate_ai_analysis(db, analysis_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"ai_analysis": analysis}
